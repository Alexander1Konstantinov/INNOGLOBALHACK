import os
import json
import requests
dev_file_path = "developers/"
host = "http://0.0.0.0:8000/"
developer_names: list[str] = [
    f.split('_desc')[0] for f in os.listdir(dev_file_path) if f.endswith('.txt')
]
avatar_path = "avatars"
def download_github_avatar(username):
    api_url = f"https://api.github.com/users/{username}"
    save_path = os.path.join(avatar_path, f"{username}.png")
    if os.path.exists(save_path):
        return save_path
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        user_data = response.json()
        avatar_url = user_data.get("avatar_url")
        if avatar_url:
            avatar_response = requests.get(avatar_url)
            avatar_response.raise_for_status()
            with open(save_path, 'wb') as file:
                file.write(avatar_response.content)
            print(f"Downloaded avatar for {username}")
            return save_path
        else:
            print(f"{username}: Avatar URL not found in the response.")
    except requests.exceptions.RequestException as e:
        print(e)
with open("embeddings.json", "r") as f:
    embedding_dict: dict[str, list[float]] = json.load(f)
with open("dataset.json", "r") as f:
    developers_dataset: list[dict[str, str]] = json.load(f)
developers_info = {
    developer["github_profile"].split("/")[-1]:
        {
            **developer,
            "nickname": developer["github_profile"].split("/")[-1]
        }
    for developer in developers_dataset
}
for developer in developer_names:
    with open(os.path.join(dev_file_path, f"{developer}_skills.json")) as f:
        local_skills = json.load(f)
    with open(os.path.join(dev_file_path, f"{developer}_desc.txt")) as f:
        local_description = f.read()
    developers_info[developer]["skills"] = local_skills
    developers_info[developer]["description"] = local_description
    developers_info[developer]["embedding"] = json.dumps(
        embedding_dict[developer])
    developers_info[developer]["profile_link"] = developers_info[developer][
        "github_profile"]
    developers_info[developer]["photo_path"] = download_github_avatar(
        developers_info[developer]["nickname"]
    )
skill_dict = {}
skill_set = set()
for developer in developer_names:
    skill_set.update(developers_info[developer]["skills"].keys())
for skill in skill_set:
    response = requests.post(f"{host}developer/skill/", json={"name": skill})
    if response.status_code not in (200, 201):
        print("Ошибка2!", response.status_code)
        print(response.text)
        continue
    data = response.json()
    skill_dict[skill] = data["id"]
for developer in developer_names:
    files = {
        "photo": (developers_info[developer]["photo_path"], open(developers_info[developer]["photo_path"], "rb"), "image/png")
    } if developers_info[developer]["photo_path"] is not None else {}
    response = requests.post(f"{host}developer/", data=developers_info[developer], files=files)
    if response.status_code not in (200, 201):
        print(developers_info[developer])
        print("Ошибка1!", response.status_code)
        print(response.text)
        continue
    data: dict[str, any] = response.json()
    developers_info[developer]["id"] = data["id"]
levels = {
    "Новичок": 1,
    "Средний": 2,
    "Продвинутый": 3
}
for developer in developer_names:
    developer_id = developers_info[developer]["id"]
    for skill_name, level in developers_info[developer]["skills"].items():
        if skill_name not in skill_dict:
            continue
        level_number: int = levels[level]
        response = requests.post(
            f"{host}developer/{developer_id}/add_skill/",
            json={
                "skill_id": skill_dict[skill_name],
                "level": level_number
            }
        )