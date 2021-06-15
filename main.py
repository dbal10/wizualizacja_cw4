from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from multiprocessing import Process
from datetime import datetime

import sys
import urllib.parse as p
import os
import pickle
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import tkinter
import pandas as pd

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def youtube_authenticate():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "credentials.json"
    creds = None
    # the file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # if there are no (valid) credentials availablle, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build(api_service_name, api_version, credentials=creds)

def get_video_details(youtube, **kwargs):
    return youtube.videos().list(
        part="snippet,contentDetails,statistics",
        **kwargs
    ).execute()


def get_video_infos(video_response):
    items = video_response.get("items")[0]
    # get the snippet, statistics & content details from the video response
    snippet = items["snippet"]
    statistics = items["statistics"]
    publish_time = snippet["publishedAt"]

    like_count = statistics["likeCount"]
    dislike_count = statistics["dislikeCount"]
    view_count = statistics["viewCount"]

    dates_array.append(publish_time)
    likes_array.append(like_count)
    dislikes_array.append(dislike_count)
    views_array.append(view_count)


def search(youtube, **kwargs):
    return youtube.search().list(
        part="snippet",
        **kwargs
    ).execute()


def write_stats(plotDates, plotDislikesPerc, plotViews, phrase, stats_file='stats.txt'):
    original_stdout = sys.stdout  # Save a reference to the original standard output

    with open(stats_file, 'a', encoding='utf-8') as f:
        sys.stdout = f  # Change the standard output to the file we created.
        print(str(plotDislikesPerc) + ',' + str(plotDates)[0:10] + ',' + str(plotViews) + ',' + phrase)
        sys.stdout = original_stdout  # Reset the standard output to its original value


def animate(i):
    graph_data = open('stats.txt', 'r').read()
    lines = graph_data.split('\n')
    xs = []
    ys = []
    ss = []
    phrases = []
    colors = ['blue', 'pink', 'red', 'green', 'cyan', 'yellow', 'orange', 'gray', 'purple', 'black']
    plt_colors = []
    i = 0

    for line in lines:
        if len(line) > 1:
            x, y, s, phrase = line.split(',')
            xs.append(float(x))
            ys.append(y)
            ss.append(float(s))
            phrases.append(phrase)
            plt_colors.append(colors[i])
            i = i + 1
    ax1.clear()

    plt.title("Publication date, % of dislikes vs views")
    plt.xlabel("% of dislikes")
    plt.ylabel("Publication date")
    plt.margins(0.15, 0.15)
    plt.autoscale()
    ax1.scatter(xs, ys, ss, alpha=0.7, c=plt_colors)
    plt.tight_layout()

    for k in range(len(phrases)):
        ax1.annotate(phrases[k], (xs[k], ys[k]), fontsize=7, horizontalalignment='center', verticalalignment='center')


def get_search_data(phrase):
    response = search(youtube, q=phrase, maxResults=5)
    items = response.get("items")
    dates_array.clear()
    views_array.clear()
    likes_array.clear()
    dislikes_array.clear()

    for item in items:
        # get the video ID
        video_id = item["id"]["videoId"]
        # get the video details
        video_response = get_video_details(youtube, id=video_id)
        # print the video details
        get_video_infos(video_response)

    date_mean = (np.array(dates_array, dtype='datetime64[D]')
                 .view('i8')
                 .mean()
                 .astype('datetime64[D]'))

    views_sum = np.array(views_array, dtype='int64').sum()
    views_sum /= 10000

    likes_sum = np.array(likes_array, dtype='int').sum()
    dislikes_sum = np.array(dislikes_array, dtype='int').sum()

    dislikes_perc = round(dislikes_sum / likes_sum * 100, 1)

    write_stats(date_mean, dislikes_perc, views_sum, phrase)


# authenticate to YouTube API
youtube = youtube_authenticate()


def draw_plot():
    ani = animation.FuncAnimation(fig, animate, interval=1000)
    plt.show()


def get_input():
    root = tkinter.Tk()
    root.title('Phrases')
    root.geometry('250x300+1480+100')

    e = tkinter.Entry(root, width=30)
    e.pack()

    def click_me():
        phrase_entered = e.get()
        get_search_data(phrase_entered)
        myLabel = tkinter.Label(root, text=e.get())
        myLabel.pack()
        e.delete(0, tkinter.END)

    myButton = tkinter.Button(root, text='Enter phrase', padx=10, pady=10, bg='white', command=click_me)
    myButton.pack()

    root.mainloop()


fig = plt.figure(figsize=(14, 9), dpi=100)
fig.canvas.set_window_title('Bubble chart')
ax1 = fig.add_subplot(1, 1, 1)

ax1.spines['left'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['top'].set_visible(False)
ax1.spines['bottom'].set_visible(False)

dates_array = []
dislikes_array = []
likes_array = []
views_array = []
plot_dates = []
plot_dislikes_perc = []
plot_views = []

if __name__ == '__main__':
    stats_file = open("stats.txt", "w")
    stats_file.close()

    p1 = Process(target=draw_plot)
    p2 = Process(target=get_input)

    p1.start()
    p2.start()

    p1.join()
    p2.join()

