import json
import re
import requests
import ollama
import sqlite3

vtubers = json.load(open("vtubers.json"))


db = sqlite3.connect("db/riots-memory.db", check_same_thread=False)
c = db.cursor()
remembered_vtubers = c.execute("SELECT * FROM people WHERE type = 'vtuber'").fetchall()

print(f"Remembered vtubers: {remembered_vtubers}")

for vtuber in vtubers:

    memory_of_vtuber = False
    for remembered_vtuber in remembered_vtubers:
        if remembered_vtuber[0] == vtuber.get('twitch'):
            memory_of_vtuber = remembered_vtuber
            break

    knowledge_of_vtuber = []
    if memory_of_vtuber:
        knowledge_of_vtuber = json.loads(memory_of_vtuber[4])

    cancel = False
    for knowledge in knowledge_of_vtuber:
        if knowledge.get('name') == 'virtualyoutuber.fandom':
            print(f"Already know about virtualyoutuber.fandom {vtuber.get('name')}")
            cancel = True
            break
    if cancel:
        continue

    url = f"https://virtualyoutuber.fandom.com/wiki/{vtuber.get('name')}?action=edit"

    response = requests.get(url)

    trimmed_response = response.content.split(b'<textarea')[1].split(b'</textarea>')[0].decode('utf-8')
    trimmed_response = trimmed_response.split("==Credits==")[0]
    split_response = trimmed_response.split("\n")
    denoised_response = []
    for line in split_response:
        if line.startswith("#") or line.startswith("{{") or line.startswith("[[") or line.startswith("==") or line.startswith("|") or line.startswith("!") or line.startswith("{{") or line == "":
            continue
        line = re.sub(r'\[.*?\]', '', line)
        line = re.sub(r'\{\{.*?\}\}', '', line)

        denoised_response.append(line)

    denoised_response = [line.strip() for line in denoised_response if line.strip()]

    denoised_response = "\n".join(denoised_response)

    if response.status_code == 200:

        messages = []
        
        messages.append({"role": "system", "content": f"You are digesting information to your long term memory system. Do not respond in sentences, only make a detailed summary of important points about the vtuber, and your feelings about them to serve as your base knowledge of them."})
        messages.append({"role": "user", "content": denoised_response})
        
        ollama_client = ollama.Client("http://localhost:11434")
        response = ollama_client.chat(model='Riot', messages=messages)

        print(f"Response: {response['message']['content']}")

        knowledge_of_vtuber.append({"name": 'virtualyoutuber.fandom', "knowledge": response["message"]["content"]})

        if memory_of_vtuber:
            c.execute("UPDATE people SET knowledge = ?, twitter_username = ?, nicknames = ? WHERE username = ?", (json.dumps(knowledge_of_vtuber), vtuber.get('twitter'), json.dumps(vtuber.get('nicknames')), vtuber.get('twitch')))
            print(f"Updated vtuber {vtuber.get('twitch')}")
        else:
            c.execute("INSERT INTO people (username, nicknames, tts_id, type, knowledge, is_ai, init_messages, twitter_username, twitter_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (vtuber.get('twitch'), json.dumps(vtuber.get('nicknames')), 0, 'streamer', json.dumps(knowledge_of_vtuber), 1, json.dumps([]), vtuber.get('twitter'), None))
            print(f"Added vtuber {vtuber.get('twitch')}")
        db.commit()
        print(f"finished vtuber {vtuber.get('twitch')}")