import datetime
import json
import re
import sqlite3
import time
import tweepy
import ollama

TEST_MODE = False

config = {}
with open("config.json") as file:
    config = json.load(file)

db = sqlite3.connect("db/riots-memory.db", check_same_thread=False)

c = db.cursor()

ollama_client = ollama.Client("http://localhost:11434")

def make_original_tweet(client):
    c.execute("SELECT * FROM tweets ORDER BY created_at DESC LIMIT 10")
    rows = c.fetchall()
    messages = [{"role": "assistant", "content": "I need to make a new tweet for my followers. Let's see my most recent tweets."}]
    for row in rows:
        messages.append({"role": "assistant", "content": f"Previous Tweet at {row[1]}:{row[0]}"})

    messages.append({"role": "assistant", "content": f"The current date is {datetime.datetime.now()}. I want to make a new tweet. Lets tweet something weird that will get people interested in following me, and watching my streams."})
    messages.append({"role": "user", "content": f"Don't talk about stream schedule, you don't have that information. Try not to reuse the same formats and ideas, come up with new ideas for each tweet. Don't bother with hashtags. Type out your exact tweet:"})
    print(f"\n\nMessages: {messages}")
    response = ollama_client.chat(model='Riot', messages=messages)
    new_tweet = re.sub(r'"', '', response['message']['content'])

    if TEST_MODE:
        print(f"TEST_MODE: Tweeting: {new_tweet}")
        c.execute("INSERT INTO tweets (message, created_at, attachments, conversation_id) VALUES (?, ?, ?, ?)", (new_tweet, str(datetime.datetime.now()), '[]', None))
        db.commit()
    else:
        print(f"Tweeting: {new_tweet}")
        client.create_tweet(text=new_tweet)
        c.execute("INSERT INTO tweets (message, created_at, attachments, conversation_id) VALUES (?, ?, ?, ?)", (new_tweet, str(datetime.datetime.now()), '[]', None))
        db.commit()
        print(f"Tweeted: {new_tweet}")

def reply_to_tweet(mentions, mention, was_mentioned=False):
    messages = []

    for user in mentions.includes['users']:
        c.execute("SELECT * FROM people WHERE twitter_username = ?", (user.username,))
        memory_of_user = c.fetchone()
        print(f"Memory of user: {memory_of_user}")
        if memory_of_user:
            messages.append({"role": "assistant", "content": f"This is what I know about @{user.username}: {memory_of_user[4]}"})

    if "referenced_tweets" in mention:
        # mention.referenced_tweets.reverse()
        for referenced_tweet in mention.referenced_tweets:
            print(f"Referenced tweet: {referenced_tweet.data}")

            for tweet in mentions.includes['tweets']:
                for user in mentions.includes['users']:
                    if str(user.id) == str(tweet.author_id):
                        if str(user.id) == str(config["X_User_ID"]):
                            messages.append({"role": "assistant", "content": tweet.text})
                        else:
                            messages.append({"role": "user", "content": f"Referenced tweet by @{user.username}: {tweet.text}"})
                        break

    author_username = ""
    for user in mentions.includes['users']:
        if user.id == mention.author_id:
            author_username = user.username
            break

    for user in mentions.includes['users']:
        memory_of_user = c.execute("SELECT * FROM people WHERE twitter_username = ?", (user.username,)).fetchone()
        print(f"Memory of user: {memory_of_user}")
        if memory_of_user:
            messages.append({"role": "assistant", "content": f"This is what I know about @{user.username}: {memory_of_user[4]}"})

    # messages.append({"role": "assistant", "content": f"This is an important test, so I should do as I am told"})

    if was_mentioned:
        messages.append({"role": "assistant", "content": f"I want to reply to this new mention from @{author_username}: {mention.text}"})
        messages.append({"role": "assistant", "content": "I am replying to someone who mentioned me on twitter. I'll try not to use gendered language because I often get the gender wrong because I can't see pictures yet."})
        messages.append({"role": "assistant", "content": "Because this is twitter, I will be extra nice and friendly because I want to make a good impression. My response will be: "})
    else:
        messages.append({"role": "assistant", "content": f"I want to reply to this tweet from @{author_username}: {mention.text}"})
        messages.append({"role": "assistant", "content": "I am replying to someone unprompted on twitter. They likely don't know me. I'll try not to use gendered language because I often get the gender wrong because I can't see pictures yet."})
        messages.append({"role": "assistant", "content": "Because this is twitter, I will be extra nice and friendly because I want to make a good impression. I will come up with a clever or silly response to the tweet, but not something mean or sarcastic, because this is not the place for that. My response will be: "})

    print(f"\n\nMessages: {messages}")

    response = ollama_client.chat(model='Riot', messages=messages)
    if response['message']['content'] != "":
        if TEST_MODE:
            print(f"TEST_MODE: Replying: {response['message']['content']} in reply to {mention.id}")
        else:
            print(f"Replying: {response['message']['content']} in reply to {mention.id}")
            client.create_tweet(text=response['message']['content'], in_reply_to_tweet_id=mention.id)
            c.execute("INSERT INTO xmentions (id, message, x_id, username, created_at, attachments, conversation_id) VALUES (?, ?, ?, ?, ?, ?, ?)", (mention.id, mention.text, mention.author_id, author_username, mention.created_at, json.dumps(mention.attachments), mention.conversation_id))
            c.execute("INSERT INTO tweets (message, created_at, attachments, conversation_id) VALUES (?, ?, ?, ?)", (response['message']['content'], str(datetime.datetime.now()), '[]', mention.conversation_id))
            db.commit()

i = 0
last_original_tweet = 0
while True:
    if not i == 0:
        print(f"Sleeping for 20 mins")
        time.sleep(1200)
    i += 1
    
    client = tweepy.Client(bearer_token=config["X_API_Bearer_Token"], access_token=config["X_API_Access_Token"], access_token_secret=config["X_API_Secret"], consumer_key=config["X_API_Consumer_Key"], consumer_secret=config["X_API_Consumer_Secret"], wait_on_rate_limit=True)

    mentions = client.get_users_mentions(id=config["X_User_ID"], max_results=5, expansions=["author_id", "referenced_tweets.id", "attachments.media_keys", "in_reply_to_user_id", "entities.mentions.username", "referenced_tweets.id.author_id"], tweet_fields=["created_at", "text", "public_metrics"], user_fields=["username", "verified", "profile_image_url"])

    print(f"Mentions: {mentions}")

    has_mention = False
    for mention in mentions.data:
        c.execute("SELECT * FROM xmentions WHERE id = ?", (mention.id,))
        row = c.fetchone()
        
        if row is None:
            has_mention = True
            print(f"\nNew mention: {mention.text}")
            print(f"    from: {mention.author_id}")
            print(f"    created_at: {mention.created_at}")
            print(f"    public_metrics: {mention.public_metrics}")
            print(f"    referenced_tweets: {mention.referenced_tweets}")
            print(f"    attachments: {mention.attachments}")
            print(f"    in_reply_to_user_id: {mention.in_reply_to_user_id}")
            print(f"    entities: {mention.entities}")
            print(f"    conversation_id: {mention.conversation_id}")

            reply_to_tweet(mentions, mention, was_mentioned=True)
            continue
        else:
            print(f"\nold mention: {mention.id}")

    if has_mention:
        continue

    if False: # disabled replies for now
        timeline = client.get_home_timeline(max_results=2, expansions=["author_id", "referenced_tweets.id", "attachments.media_keys", "in_reply_to_user_id", "entities.mentions.username", "referenced_tweets.id.author_id"], tweet_fields=["created_at", "text", "public_metrics"], user_fields=["username", "verified", "profile_image_url"])
        print(f"Timeline: {timeline}")

        messages = [{"role": "assistant", "content": "I'm Starting New Twitter Interaction. I should be nice. I want to make friends with other cute vtubers!"}]

        for tweet in timeline.data:
            print(f"Tweet: {tweet}")
            print(f"    from: {tweet.author_id}")
            print(f"    created_at: {tweet.created_at}")
            print(f"    public_metrics: {tweet.public_metrics}")
            print(f"    referenced_tweets: {tweet.referenced_tweets}")
            print(f"    attachments: {tweet.attachments}")
            print(f"    in_reply_to_user_id: {tweet.in_reply_to_user_id}")
            print(f"    entities: {tweet.entities}")
            print(f"    conversation_id: {tweet.conversation_id}")

            user = next((user for user in timeline.includes['users'] if user.id == tweet.author_id), None)
            if user:
                username = user.username
            else:
                username = ""

            # if not tweet.attachments: # ignore tweets with media until we can handle them
            messages.append({"role": "assistant", "content": f"New tweet ID:{tweet.id} from @{username}: {tweet.text}"})

        messages.append({"role": "user", "content": f"select a tweet id from the list above that you want to reply to."})
        print(f"\n\nMessages: {messages}")
        response = ollama_client.chat(model='Riot', messages=messages)
        print(f"{response['message']['content']}")

        tweet_id = re.findall(r'\d+', response['message']['content'])[0]
        print(f"Tweet ID: {tweet_id}")
        for tweet in timeline.data:
            print(f"Tweet: {tweet.id}")
            if str(tweet.id) == str(tweet_id):
                reply_to_tweet(timeline, tweet)
    else:
        print(f"No new mentions found")
        #Original Tweet
        if last_original_tweet == 0 or (datetime.datetime.now() - last_original_tweet).total_seconds() > (60 * 60 * 2):
            last_original_tweet = datetime.datetime.now()
            make_original_tweet(client)
        continue

