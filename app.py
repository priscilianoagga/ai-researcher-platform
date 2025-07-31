# app.py - 主应用文件
from flask import Flask, render_template, jsonify, request, session
import pandas as pd
import json
import tweepy
import os
from datetime import datetime, timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import logging

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# X API 配置 (从环境变量获取)
TWITTER_BEARER_TOKEN = os.environ.get('TWITTER_BEARER_TOKEN')
TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')


class ResearcherManager:
    def __init__(self):
        self.init_database()
        self.load_researchers_data()

    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect('research_platform.db')
        cursor = conn.cursor()

        # 创建研究者表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS researchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rank INTEGER,
                name TEXT NOT NULL,
                country TEXT,
                company TEXT,
                research_focus TEXT,
                x_account TEXT,
                followers_count INTEGER DEFAULT 0,
                following_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建内容表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS x_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                researcher_id INTEGER,
                tweet_id TEXT UNIQUE,
                content TEXT,
                content_type TEXT,
                media_urls TEXT,
                likes_count INTEGER DEFAULT 0,
                retweets_count INTEGER DEFAULT 0,
                replies_count INTEGER DEFAULT 0,
                posted_at DATETIME,
                collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (researcher_id) REFERENCES researchers (id)
            )
        ''')

        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def load_researchers_data(self):
        """从Excel文件加载研究者数据"""
        try:
            # 这里应该读取用户上传的Excel文件
            # 暂时使用模拟数据
            researchers_data = [
                {
                    'rank': 1,
                    'name': 'Ilya Sutskever',
                    'country': 'Canada',
                    'company': 'SSI',
                    'research_focus': 'AlexNet、Seq2seq、深度学习',
                    'x_account': '@ilyasut'
                },
                {
                    'rank': 2,
                    'name': 'Noam Shazeer',
                    'country': 'USA',
                    'company': 'Google Deepmind',
                    'research_focus': '注意力机制即你所需要、混合专家模型、角色AI',
                    'x_account': '@noamshazeer'
                },
                {
                    'rank': 3,
                    'name': 'Geoffrey Hinton',
                    'country': 'UK',
                    'company': 'University of Toronto',
                    'research_focus': '反向传播、玻尔兹曼机、深度学习',
                    'x_account': '@geoffreyhinton'
                },
                {
                    'rank': 4,
                    'name': 'Alec Radford',
                    'country': 'USA',
                    'company': 'Thinking Machines',
                    'research_focus': '生成对抗网络、GPT、CLIP',
                    'x_account': '@alec_radford'
                },
                {
                    'rank': 5,
                    'name': 'Andrej Karpathy',
                    'country': 'Slovakia',
                    'company': 'Tesla',
                    'research_focus': '计算机视觉、神经网络、自动驾驶',
                    'x_account': '@karpathy'
                }
            ]

            conn = sqlite3.connect('research_platform.db')
            cursor = conn.cursor()

            for researcher in researchers_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO researchers 
                    (rank, name, country, company, research_focus, x_account)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    researcher['rank'],
                    researcher['name'],
                    researcher['country'],
                    researcher['company'],
                    researcher['research_focus'],
                    researcher['x_account']
                ))

            conn.commit()
            conn.close()
            logger.info("研究者数据加载完成")

        except Exception as e:
            logger.error(f"加载研究者数据失败: {e}")


class TwitterAPI:
    def __init__(self):
        if TWITTER_BEARER_TOKEN:
            self.client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
        else:
            self.client = None
            logger.warning("Twitter API未配置")

    def get_user_tweets(self, username, max_results=20):
        """获取用户推文"""
        if not self.client:
            return self.mock_tweets_data(username)

        try:
            # 移除@符号
            username = username.replace('@', '')

            # 获取用户信息
            user = self.client.get_user(username=username)
            if not user.data:
                return []

            # 获取推文
            tweets = self.client.get_users_tweets(
                id=user.data.id,
                max_results=max_results,
                tweet_fields=['created_at', 'public_metrics', 'attachments'],
                expansions=['attachments.media_keys'],
                media_fields=['type', 'url', 'preview_image_url']
            )

            return self.format_tweets_data(tweets, username)

        except Exception as e:
            logger.error(f"获取推文失败 {username}: {e}")
            return self.mock_tweets_data(username)

    def mock_tweets_data(self, username):
        """模拟推文数据"""
        mock_data = [
            {
                'id': f'mock_{username}_1',
                'content': f'Exciting developments in AI research! The future of AGI is bright. #{username}',
                'type': 'text',
                'likes': 1247,
                'retweets': 389,
                'replies': 156,
                'posted_at': datetime.now() - timedelta(hours=2),
                'media_urls': []
            },
            {
                'id': f'mock_{username}_2',
                'content': f'Sharing insights from our latest research paper on neural networks.',
                'type': 'text',
                'likes': 856,
                'retweets': 234,
                'replies': 89,
                'posted_at': datetime.now() - timedelta(hours=6),
                'media_urls': ['https://via.placeholder.com/600x400?text=Research+Image']
            }
        ]
        return mock_data

    def format_tweets_data(self, tweets, username):
        """格式化推文数据"""
        formatted_tweets = []

        if not tweets.data:
            return formatted_tweets

        for tweet in tweets.data:
            formatted_tweet = {
                'id': tweet.id,
                'content': tweet.text,
                'type': 'text',
                'likes': tweet.public_metrics['like_count'],
                'retweets': tweet.public_metrics['retweet_count'],
                'replies': tweet.public_metrics['reply_count'],
                'posted_at': tweet.created_at,
                'media_urls': []
            }

            # 处理媒体附件
            if hasattr(tweet, 'attachments') and tweet.attachments:
                if 'media_keys' in tweet.attachments:
                    formatted_tweet['type'] = 'media'
                    # 这里需要处理媒体URL，简化处理
                    formatted_tweet['media_urls'] = ['https://via.placeholder.com/600x400?text=Media+Content']

            formatted_tweets.append(formatted_tweet)

        return formatted_tweets


# 初始化管理器
researcher_manager = ResearcherManager()
twitter_api = TwitterAPI()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/researchers')
def get_researchers():
    """获取研究者列表"""
    conn = sqlite3.connect('research_platform.db')
    cursor = conn.cursor()

    search_query = request.args.get('search', '')

    if search_query:
        cursor.execute('''
            SELECT * FROM researchers 
            WHERE name LIKE ? OR company LIKE ? OR research_focus LIKE ?
            ORDER BY rank
        ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute('SELECT * FROM researchers ORDER BY rank')

    researchers = []
    for row in cursor.fetchall():
        researchers.append({
            'id': row[0],
            'rank': row[1],
            'name': row[2],
            'country': row[3],
            'company': row[4],
            'research_focus': row[5],
            'x_account': row[6],
            'followers_count': row[7],
            'following_count': row[8]
        })

    conn.close()
    return jsonify(researchers)


@app.route('/api/researcher/<int:researcher_id>/content')
def get_researcher_content(researcher_id):
    """获取特定研究者的内容"""
    conn = sqlite3.connect('research_platform.db')
    cursor = conn.cursor()

    # 获取研究者信息
    cursor.execute('SELECT * FROM researchers WHERE id = ?', (researcher_id,))
    researcher = cursor.fetchone()

    if not researcher:
        return jsonify({'error': 'Researcher not found'}), 404

    x_account = researcher[6]  # x_account字段

    # 获取或抓取推文数据
    tweets = twitter_api.get_user_tweets(x_account)

    # 保存到数据库
    for tweet in tweets:
        cursor.execute('''
            INSERT OR REPLACE INTO x_content 
            (researcher_id, tweet_id, content, content_type, media_urls, 
             likes_count, retweets_count, replies_count, posted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            researcher_id,
            tweet['id'],
            tweet['content'],
            tweet['type'],
            json.dumps(tweet['media_urls']),
            tweet['likes'],
            tweet['retweets'],
            tweet['replies'],
            tweet['posted_at']
        ))

    conn.commit()
    conn.close()

    return jsonify(tweets)


@app.route('/api/content')
def get_all_content():
    """获取所有内容"""
    conn = sqlite3.connect('research_platform.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT c.*, r.name, r.x_account 
        FROM x_content c
        JOIN researchers r ON c.researcher_id = r.id
        ORDER BY c.posted_at DESC
        LIMIT 50
    ''')

    content_list = []
    for row in cursor.fetchall():
        content_list.append({
            'id': row[0],
            'content': row[2],
            'content_type': row[3],
            'media_urls': json.loads(row[4]) if row[4] else [],
            'likes_count': row[5],
            'retweets_count': row[6],
            'replies_count': row[7],
            'posted_at': row[8],
            'author_name': row[10],
            'author_handle': row[11]
        })

    conn.close()
    return jsonify(content_list)


@app.route('/api/analytics')
def get_analytics():
    """获取分析数据"""
    conn = sqlite3.connect('research_platform.db')
    cursor = conn.cursor()

    # 研究者总数
    cursor.execute('SELECT COUNT(*) FROM researchers')
    total_researchers = cursor.fetchone()[0]

    # 内容总数
    cursor.execute('SELECT COUNT(*) FROM x_content')
    total_content = cursor.fetchone()[0]

    # 总互动数
    cursor.execute('SELECT SUM(likes_count + retweets_count + replies_count) FROM x_content')
    total_engagement = cursor.fetchone()[0] or 0

    # 内容类型分布
    cursor.execute('''
        SELECT content_type, COUNT(*) 
        FROM x_content 
        GROUP BY content_type
    ''')
    content_distribution = dict(cursor.fetchall())

    # 国家分布
    cursor.execute('''
        SELECT country, COUNT(*) 
        FROM researchers 
        GROUP BY country 
        ORDER BY COUNT(*) DESC
    ''')
    country_distribution = dict(cursor.fetchall())

    conn.close()

    return jsonify({
        'total_researchers': total_researchers,
        'total_content': total_content,
        'total_engagement': total_engagement,
        'content_distribution': content_distribution,
        'country_distribution': country_distribution
    })


@app.route('/api/upload_excel', methods=['POST'])
def upload_excel():
    """上传Excel文件"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        # 读取Excel文件
        df = pd.read_excel(file)

        # 清理和验证数据
        required_columns = ['排名', '姓名', '国家', '所在公司', '研究方向和成就（中文）', 'X账号']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': 'Excel格式不正确'}), 400

        # 保存到数据库
        conn = sqlite3.connect('research_platform.db')
        cursor = conn.cursor()

        for _, row in df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO researchers 
                (rank, name, country, company, research_focus, x_account)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                int(row['排名']),
                str(row['姓名']),
                str(row['国家']),
                str(row['所在公司']),
                str(row['研究方向和成就（中文）']),
                str(row['X账号'])
            ))

        conn.commit()
        conn.close()

        return jsonify({'message': f'成功导入 {len(df)} 位研究者数据'})

    except Exception as e:
        logger.error(f"Excel上传处理失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/start_monitoring', methods=['POST'])
def start_monitoring():
    """开始监控研究者"""
    data = request.get_json()
    researcher_ids = data.get('researcher_ids', [])

    if not researcher_ids:
        return jsonify({'error': 'No researchers selected'}), 400

    try:
        # 这里可以启动后台任务来定期抓取内容
        # 简化处理，直接返回成功
        return jsonify({
            'message': f'开始监控 {len(researcher_ids)} 位研究者',
            'researcher_ids': researcher_ids
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

# requirements.txt 文件内容:
"""
Flask==2.3.3
pandas==2.1.0
tweepy==4.14.0
sqlite3
Werkzeug==2.3.7
gunicorn==21.2.0
python-dotenv==1.0.0
openpyxl==3.1.2
"""

# railway.toml 部署配置:
"""
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn app:app"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[env]
PYTHON_VERSION = "3.11"
"""

# .env 环境变量配置:
"""
TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAAlZ3QEAAAAAI7CwJ2gxUwJH%2B9tOEBs3UwSFbKQ%3DgZy78b69CsGpaOKKb0oTHBOSiHeIjBA0XGoZmCruPcTEXGnDL5
"""