import os
import zipfile
import json
from collections import Counter
import chardet
from data_prep import DataPrep
from llm_skill_extractor import LLMHandler
from tqdm import tqdm
def check_archive_paths_in_directory(json_file_path, directory_path):
    # Загружаем данные из JSON-файла
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    # Проходим по каждому элементу и проверяем существование файла
    for item in data:
        archive_path = item.get('archive_path')
        full_path = os.path.join(directory_path, archive_path)
        if os.path.exists(full_path):
            return True
        else:
            return False
def extract_repo(developer):
    extract_path = f"unzip_repo/unzip_{developer['archive_path'].split('/')[-1].split('.zi')[0]}"
    with zipfile.ZipFile(developer['archive_path'], 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    return extract_path
def get_skills_and_desc(developer, prep_data, llm_h, repo_path, printed=True):
    author_id = [
        developer['email'],
        developer['github_profile'].split('/')[-1],
        developer['name']
    ]
    architecture = prepare_architecture(data, author_id, repo_path, 5, llm_h)
    # Получение добавленных кодов в 20 наибольших коммитах
    style_rating = prepare_styles(data, author_id, repo_path, 10, llm_h)
    commits = prep_data.get_commits_by_author(author_id, repo_path)
    t = prep_data.get_time_last_commit(author_id)
    codes = prep_data.get_last_n_largest_commits(commits, t, 20, True)
    commit_descriptions = llm_h.get_code_commit_description(codes)
    skills = llm_h.get_developer_skills_levels(commit_descriptions)
    if printed:
        print(skills)
    comments = llm_h.get_comments(commit_descriptions)
    for_desc = "\nКомпетенции: " + json.dumps(skills, default=lambda x: dict(x)) + "\nКомментарии:\n" + comments
    desc = llm_h.evaluate_commits_with_llm(llm_h.prepare_prompt_developer_desc(for_desc))
    if printed:
        print(desc)
    return author_id[1], style_rating, skills, desc, architecture
def prepare_styles(data, author_id, repo_path, n, llm_h):
    prepared = []
    codes = data.get_added_commits(author_id, repo_path, n)
    for code in codes:
        try:
            prepared.append(json.loads(llm_h.llama_style(llm_h.prepare_prompt_style(code))))
        except:
            continue
    ratings = [list(rating.values())[0] for rating in prepared]
    ratings = Counter(ratings)
    rating = f'Соответствие стилевым конвенциям языка: {max(ratings, key=lambda x: ratings[x])}'
    return rating
def prepare_architecture(data, author_id, repo_path, n, llm_h):
    added_removed_descr = data.get_added_removed_descr(author_id, repo_path, n, llm_h)
    prompt_architecture = [llm_h.prepare_prompt_architecture(descr) for descr in added_removed_descr]
    architectures = []
    for prompt in prompt_architecture:
        try:
            architectures.append(json.loads(llm_h.llama_style(prompt)))
        except:
            continue
    descrs = [list(descr.values())[0] for descr in architectures]
    descrs = Counter(descrs)
    descr = f'Участие в архитектурных решениях: {max(descrs, key=lambda x: descrs[x])}'
    return descr
def change_desc(llm_h):
    developers_desc = [f"developers/{f}" for f in os.listdir("developers") if f.endswith('.txt')]
    new_descriptions = []
    for i, name in enumerate(developers_desc):
        with open(name, 'rb') as file:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']
        with open(name, 'r', encoding=encoding) as file:
            desc = file.read()
        new_desc = llm_h.evaluate_commits_with_llm(llm_h.prepare_prompt_compression_desc(desc))
        new_descriptions.append(new_desc)
        with open(name, 'w', encoding='utf-8') as txt_file:
            txt_file.write(new_desc)
    print(new_descriptions)
if __name__ == '__main__':
    data_path = "C:\innoglobalhack\Hackaton"
    os.chdir(data_path)
    data = DataPrep(data_path=data_path)
    llm_handler = LLMHandler()
    for i, dev in tqdm(enumerate(data.read_dataset())):
        os.chdir(data_path)
        folder_path = dev['archive_path'].split('.')
        folder_path = '.'.join(folder_path[:-1])
        if not os.path.exists(folder_path):
            continue
        try:
            id, style_rating, skills, dev_desc, architecture = get_skills_and_desc(dev, data, llm_handler, folder_path)
        except:
            continue
        os.chdir(data_path + "/processed_data")
        with open(f'{id}_skills.json', 'w', encoding='utf-8') as json_file:
            json.dump(skills, json_file)
        with open(f'{id}_desc.txt', 'w', encoding='utf-8') as txt_file:
            txt_file.write(dev_desc)
        with open(f'{id}_style.txt', 'w', encoding='utf-8') as txt_file:
            txt_file.write(style_rating)
        with open(f'{id}_architecture.txt', 'w', encoding='utf-8') as txt_file:
            txt_file.write(architecture)
        os.chdir(data_path)
    change_desc(llm_handler)