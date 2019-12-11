#! /usr/bin/env python

import json


with open('/Users/delron/Downloads/news.json', 'r') as f:
    with open('./article_data.sql', 'w') as df:
        for i in range(24):
            l = f.readline()
            article = json.loads(l)
            sql = "insert into news_article_basic(article_id, user_id, channel_id, title, cover, status)"
            sql += """values({}, 1, 1, '{}', '{{"type":0, "images":[]}}', 2);\n""".format(i+1, article['title'])
            df.write(sql)
            sql = "insert into news_article_content(article_id, content) values({},".format(i+1)
            sql += repr(article['content'])
            sql += ");\n"
            df.write(sql)
