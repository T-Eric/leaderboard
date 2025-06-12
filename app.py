from datetime import datetime
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
import requests
from werkzeug.utils import secure_filename
import sys
import os
import click

# init
app = Flask(__name__)
app.config['SECRET_KEY'] = 'thisisasecretkey'  # TODO 暂时没有dotenv配置
app.config['SQLALCHEMY_DATABASE_URI'] = ('sqlite:///' if sys.platform.startswith(
    'win') else 'sqlite:////') + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# login_manager = LoginManager(app)
# login_manager.login_view = 'login'

SERVER_IP = '10.181.70.149'
OJ_TOKEN = 'acmoj-9b00d190090e0303fc684d1341e9918d'

# 仓库类型和题目ID的映射关系
REPOSITORY_PROBLEM_MAPPING = {
    'basic': [2510],
    'book': [1075, 1775],
    'icpc': [1986],
    'minesweeper': [2395],
    'python': [2515],
    'ticket': [1867]
}

# database


class Model(db.Model):
    __tablename__ = 'models'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    description = db.Column(db.String(128))
    organization = db.Column(db.String(64), nullable=True)

    submission = db.relationship(
        'Submission', backref='model', lazy='dynamic', order_by="desc(Submission.submission_time)")

    def __repr__(self):
        return f"<Model {self.id}: {self.name}>"


class Submission(db.Model):
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, nullable=False)
    submission_time = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True)  # index=True 加速排序
    score = db.Column(db.Float, nullable=True)
    details = db.Column(db.Text, nullable=True)
    git_daemon_pid = db.Column(db.Integer, nullable=True)  # 存储Git Daemon的PID
    git_repos_path = db.Column(db.String(256), nullable=True)  # 存储临时Git目录路径

    # 存储OJ提交ID
    basic_submission_id = db.Column(db.Integer, nullable=True)
    book_submission_id = db.Column(db.Integer, nullable=True)
    book_second_submission_id = db.Column(
        db.Integer, nullable=True)  # 存储Book仓库第二个提交
    icpc_submission_id = db.Column(db.Integer, nullable=True)
    minesweeper_submission_id = db.Column(db.Integer, nullable=True)
    python_submission_id = db.Column(db.Integer, nullable=True)
    ticket_submission_id = db.Column(db.Integer, nullable=True)

    # 存储各仓库评测状态
    basic_status = db.Column(db.String(32), nullable=True)
    book_status = db.Column(db.String(32), nullable=True)
    book_second_status = db.Column(
        db.String(32), nullable=True)  # 存储Book仓库第二个提交状态
    icpc_status = db.Column(db.String(32), nullable=True)
    minesweeper_status = db.Column(db.String(32), nullable=True)
    python_status = db.Column(db.String(32), nullable=True)
    ticket_status = db.Column(db.String(32), nullable=True)

    # 存储各仓库得分
    basic_score = db.Column(db.Float, nullable=True)
    book_score = db.Column(db.Float, nullable=True)
    book_second_score = db.Column(db.Float, nullable=True)  # 存储Book仓库第二个提交分数
    icpc_score = db.Column(db.Float, nullable=True)
    minesweeper_score = db.Column(db.Float, nullable=True)
    python_score = db.Column(db.Float, nullable=True)
    ticket_score = db.Column(db.Float, nullable=True)

    model_id = db.Column(db.Integer, db.ForeignKey(
        'models.id'), nullable=False)

    def __repr__(self):
        return f"<Submission {self.id} for Model ID {self.model_id} at {self.submission_time}>"

    def to_dict(self):
        return {
            'id': self.id,
            'model_id': self.model_id,
            'model_name': self.model.name if self.model else None,
            'submission_time': self.submission_time.isoformat(),
            'score': self.score,
            'details': self.details,
            'repositories': {
                'basic': {'id': self.basic_submission_id, 'status': self.basic_status, 'score': self.basic_score},
                'book': {'id': self.book_submission_id, 'status': self.book_status, 'score': self.book_score},
                'book_second': {'id': self.book_second_submission_id, 'status': self.book_second_status, 'score': self.book_second_score},
                'icpc': {'id': self.icpc_submission_id, 'status': self.icpc_status, 'score': self.icpc_score},
                'minesweeper': {'id': self.minesweeper_submission_id, 'status': self.minesweeper_status, 'score': self.minesweeper_score},
                'python': {'id': self.python_submission_id, 'status': self.python_status, 'score': self.python_score},
                'ticket': {'id': self.ticket_submission_id, 'status': self.ticket_status, 'score': self.ticket_score}
            }
        }

    def all_finished_compiling(self):
        """检查是否所有仓库都已完成编译（不是pending或compiling状态）"""
        statuses = [
            self.basic_status, self.book_status, self.book_second_status, self.icpc_status,
            self.minesweeper_status, self.python_status, self.ticket_status
        ]
        for status in statuses:
            if not status or status.lower() in ['pending', 'compiling']:
                return False
        return True

    def calculate_total_score(self):
        """计算总分"""
        scores = [
            self.basic_score, self.book_score, self.icpc_score,
            self.minesweeper_score, self.python_score, self.ticket_score
        ]

        # 过滤掉None值
        valid_scores = [s for s in scores if s is not None]
        if valid_scores:
            self.score = sum(valid_scores) / len(valid_scores)
        return self.score


def create_model(name, description, organization='Nope'):
    model = Model(name=name, description=description,
                  organization=organization)
    db.session.add(model)
    db.session.commit()
    return model


def create_submission(model_id, score, details):
    submission = Submission(model_id=model_id, score=score, details=details)
    db.session.add(submission)
    db.session.commit()
    return submission


def get_model_by_name(name):
    return Model.query.filter_by(name=name).first()


def match_repository_type(repo_name):
    """根据仓库名称匹配仓库类型，不区分大小写"""
    repo_name_lower = repo_name.lower()
    for repo_type in REPOSITORY_PROBLEM_MAPPING.keys():
        if repo_type.lower() in repo_name_lower:
            return repo_type
    return None


# daemon handler
class GitDaemonManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.pid = None

    def start_daemon(self):
        """启动Git Daemon服务"""
        proc = subprocess.Popen(
            ['git', 'daemon', '--reuseaddr',
                f'--base-path={self.base_path}', '--export-all'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.pid = proc.pid
        return self.pid

    def stop_daemon(self):
        """停止Git Daemon服务"""
        if self.pid:
            try:
                os.kill(self.pid, 15)  # SIGTERM
                return True
            except OSError:
                return False
        return False


def extract_zip_flat(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # 获取 zip 内所有文件路径
        members = zip_ref.namelist()

        # 自动识别 zip 中的"公共前缀"路径，即顶层目录
        common_prefix = os.path.commonprefix(members)
        if not common_prefix.endswith('/'):
            # 若只是文件名前缀，不是路径，改成路径形式
            common_prefix = os.path.dirname(common_prefix) + '/'

        for member in members:
            # 去掉顶层路径前缀
            member_rel_path = member[len(common_prefix):] if member.startswith(
                common_prefix) else member

            if member_rel_path:
                target_path = os.path.join(extract_to, member_rel_path)

                if member.endswith('/'):
                    os.makedirs(target_path, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                        target.write(source.read())


def check_submission_status(submission_id):
    """
    定期检查提交状态，监控OJ评测结果，当所有仓库不再处于pending或compiling状态后关闭Git Daemon
    """
    try:
        submission = Submission.query.get(submission_id)
        if not submission:
            print(f"Error: Submission {submission_id} not found")
            return

        # 获取所有提交ID
        submission_ids = {
            'basic': submission.basic_submission_id,
            'book': submission.book_submission_id,
            'book_second': submission.book_second_submission_id,
            'icpc': submission.icpc_submission_id,
            'minesweeper': submission.minesweeper_submission_id,
            'python': submission.python_submission_id,
            'ticket': submission.ticket_submission_id
        }

        # 筛选掉None值
        submission_ids = {k: v for k,
                          v in submission_ids.items() if v is not None}

        if not submission_ids:
            print("No submission IDs available to monitor")
            return

        max_checks = 720  # 最多检查720次，约1小时
        check_interval = 5  # 每5秒检查一次
        check_count = 0

        while check_count < max_checks:
            check_count += 1
            all_finished_compiling = True

            # 检查每个仓库的评测状态
            for repo_name, oj_submission_id in submission_ids.items():
                try:
                    # 调用OJ API获取评测状态
                    response = requests.get(
                        f"https://acm.sjtu.edu.cn/OnlineJudge/api/v1/submission/{oj_submission_id}",
                        headers={
                            'accept': 'application/json',
                            'Authorization': f'Bearer {OJ_TOKEN}'
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        status = result.get('status', '')
                        score = result.get('score')

                        # 更新数据库中的状态和分数
                        setattr(submission, f"{repo_name}_status", status)
                        if score is not None:
                            setattr(
                                submission, f"{repo_name}_score", float(score))

                            # 特殊处理book评分：如果两个book提交都有分数，取平均值
                            if repo_name == 'book' or repo_name == 'book_second':
                                if submission.book_score is not None and submission.book_second_score is not None:
                                    # 将book的score设置为两次提交的平均值
                                    avg_score = (
                                        submission.book_score + submission.book_second_score) / 2
                                    submission.book_score = avg_score

                        # 检查是否需要继续监控 - 当状态是pending或compiling时继续监控
                        if status.lower() in ['pending', 'compiling']:
                            all_finished_compiling = False
                    else:
                        print(
                            f"API request failed for {repo_name}: {response.status_code}")
                        all_finished_compiling = False
                except Exception as e:
                    print(f"Error checking {repo_name} status: {e}")
                    all_finished_compiling = False

            # 更新数据库
            submission.calculate_total_score()
            db.session.commit()

            # 如果所有仓库都不再处于pending或compiling状态，则停止监控并关闭Git Daemon
            if all_finished_compiling:
                print("All repositories finished compiling, closing Git Daemon")
                break

            # 等待下一次检查
            time.sleep(check_interval)

        # 关闭Git Daemon
        if submission.git_daemon_pid:
            try:
                os.kill(submission.git_daemon_pid, 15)  # SIGTERM
                submission.git_daemon_pid = None
                submission.details += "\nGit Daemon 已关闭"
                db.session.commit()
                print("Git Daemon has been closed")

                # 清理临时目录
                if submission.git_repos_path and os.path.exists(submission.git_repos_path):
                    shutil.rmtree(submission.git_repos_path)
                    submission.details += "\n临时目录已清理"
                    submission.git_repos_path = None
                    db.session.commit()
            except OSError as e:
                submission.details += f"\n尝试关闭 Git Daemon 失败: {str(e)}"
                db.session.commit()
                print(f"Failed to close Git Daemon: {e}")
    except Exception as e:
        print(f"Error in check_submission_status: {e}")
        try:
            submission = Submission.query.get(submission_id)
            if submission:
                submission.details += f"\n监控评测状态出错: {str(e)}"
                db.session.commit()
        except:
            print(f"[严重错误] 无法更新数据库: {e}")


def update_submission_status(submission):
    """更新提交的评测状态"""
    # 遍历所有提交ID并更新状态
    submission_ids = {
        'basic': submission.basic_submission_id,
        'book': submission.book_submission_id,
        'book_second': submission.book_second_submission_id,
        'icpc': submission.icpc_submission_id,
        'minesweeper': submission.minesweeper_submission_id,
        'python': submission.python_submission_id,
        'ticket': submission.ticket_submission_id
    }

    # 筛选掉None值
    submission_ids = {k: v for k, v in submission_ids.items() if v is not None}

    # 检查每个仓库的评测状态
    for repo_name, oj_submission_id in submission_ids.items():
        try:
            # 调用OJ API获取评测状态
            response = requests.get(
                f"https://acm.sjtu.edu.cn/OnlineJudge/api/v1/submission/{oj_submission_id}",
                headers={
                    'accept': 'application/json',
                    'Authorization': f'Bearer {OJ_TOKEN}'
                }
            )

            if response.status_code == 200:
                result = response.json()
                status = result.get('status', '')
                score = result.get('score')

                # 更新数据库中的状态和分数
                setattr(submission, f"{repo_name}_status", status)
                if score is not None:
                    setattr(submission, f"{repo_name}_score", float(score))

                    # 特殊处理book评分：如果两个book提交都有分数，取平均值
                    if repo_name == 'book' or repo_name == 'book_second':
                        if submission.book_score is not None and submission.book_second_score is not None:
                            # 将book的score设置为两次提交的平均值
                            avg_score = (submission.book_score +
                                         submission.book_second_score) / 2
                            submission.book_score = avg_score
        except Exception as e:
            print(f"Error checking {repo_name} status: {e}")

    # 计算总分并更新数据库
    submission.calculate_total_score()
    db.session.commit()


def process_git_submission(submission_id, model_id, zip_path):
    temp_dir = None
    try:
        submission = Submission.query.get(submission_id)
        model = Model.query.get(model_id)

        if not submission or not model:
            raise Exception("找不到提交记录或模型")

        # 创建临时目录并解压 zip 文件
        temp_dir = tempfile.mkdtemp(
            prefix=f"git_repos_{submission_id}_", dir="/tmp")

        extract_zip_flat(zip_path, temp_dir)

        # 假设 zip 中是多个子目录，每个对应一个 repo
        repo_dirs = sorted(
            [os.path.join(temp_dir, d) for d in os.listdir(temp_dir)
             if os.path.isdir(os.path.join(temp_dir, d))]
        )
        repo_names = [os.path.basename(repo_dir) for repo_dir in repo_dirs]
        print(f"Repo Names: {repo_names}")

        # 映射仓库名到仓库类型
        repo_type_mapping = {}
        for repo_dir in repo_dirs:
            repo_name = os.path.basename(repo_dir)
            repo_type = match_repository_type(repo_name)

            if repo_type:
                if repo_type in repo_type_mapping:
                    # 多个文件夹匹配到同一个仓库类型
                    submission.details = f"错误: 多个文件夹匹配到同一个仓库类型 '{repo_type}'。文件夹: {repo_type_mapping[repo_type]}, {repo_name}"
                    db.session.commit()
                    return
                repo_type_mapping[repo_type] = repo_dir

        # 检查是否所有仓库类型都匹配到了
        missing_types = set(REPOSITORY_PROBLEM_MAPPING.keys()
                            ) - set(repo_type_mapping.keys())
        if missing_types:
            submission.details = f"错误: 以下仓库类型未找到匹配的文件夹: {', '.join(missing_types)}"
            db.session.commit()
            return

        # 特殊检查Minesweeper的server.h文件
        if 'minesweeper' in repo_type_mapping:
            minesweeper_dir = repo_type_mapping['minesweeper']
            server_h_path = os.path.join(minesweeper_dir, 'server.h')
            if not os.path.exists(server_h_path):
                submission.details = f"错误: Minesweeper仓库中找不到server.h文件"
                db.session.commit()
                return

        # 初始化并提交 Git 仓库 (除了Minesweeper)
        for repo_type, repo_dir in repo_type_mapping.items():
            if repo_type != 'minesweeper':  # 跳过Minesweeper，它将使用不同的提交方法
                subprocess.run(['git', 'init'], cwd=repo_dir, check=True)
                subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)
                subprocess.run(
                    ['git', 'config', 'user.email', 'you@example.com'], cwd=repo_dir, check=True)
                subprocess.run(
                    ['git', 'config', 'user.name', 'Your Name'], cwd=repo_dir, check=True)
                subprocess.run(
                    ['git', 'commit', '-m', 'Initial commit'], cwd=repo_dir, check=True)
                export_ok_path = os.path.join(
                    repo_dir, '.git', 'git-daemon-export-ok')
                open(export_ok_path, 'w').close()

        # 启动 Git Daemon 服务
        git_manager = GitDaemonManager(temp_dir)
        daemon_pid = git_manager.start_daemon()

        # 更新提交记录
        submission.git_repos_path = temp_dir
        submission.git_daemon_pid = daemon_pid
        db.session.commit()

        time.sleep(2)  # 等待 Git Daemon 完全启动

        # 处理Minesweeper特殊提交
        if 'minesweeper' in repo_type_mapping:
            minesweeper_dir = repo_type_mapping['minesweeper']
            server_h_path = os.path.join(minesweeper_dir, 'server.h')
            with open(server_h_path, 'r') as f:
                server_h_code = f.read()

            # 提交Minesweeper的server.h作为CPP代码
            problem_id = REPOSITORY_PROBLEM_MAPPING['minesweeper'][0]  # 2395
            response = requests.post(
                f"https://acm.sjtu.edu.cn/OnlineJudge/api/v1/problem/{problem_id}/submit",
                headers={
                    'accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': f'Bearer {OJ_TOKEN}'
                },
                data={
                    'public': 'false',
                    'language': 'cpp',
                    'code': server_h_code
                }
            )

            if response.status_code == 201:
                result = response.json()
                oj_submission_id = result.get('id')
                submission.minesweeper_submission_id = oj_submission_id
                submission.details += f"\nMinesweeper仓库的server.h文件以CPP语言提交到题目{problem_id}，OJ提交ID: {oj_submission_id}"
                db.session.commit()
            else:
                submission.details += f"\nMinesweeper仓库提交到题目{problem_id}失败: {response.status_code} - {response.text}"
                db.session.commit()

            time.sleep(2)  # 避免API请求过快

        # 提交其他仓库到对应题目
        for repo_type, repo_dir in repo_type_mapping.items():
            if repo_type != 'minesweeper':  # 跳过Minesweeper，它已经单独处理
                repo_name = os.path.basename(repo_dir)
                problem_ids = REPOSITORY_PROBLEM_MAPPING[repo_type]

                for i, problem_id in enumerate(problem_ids):
                    # 构建git协议URL
                    git_url = f"git://{SERVER_IP}/{repo_name}"

                    # API调用
                    response = requests.post(
                        f"https://acm.sjtu.edu.cn/OnlineJudge/api/v1/problem/{problem_id}/submit",
                        headers={
                            'accept': 'application/json',
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'Authorization': f'Bearer {OJ_TOKEN}'
                        },
                        data={
                            'public': 'false',
                            'language': 'git',
                            'code': git_url
                        }
                    )

                    if response.status_code == 201:
                        result = response.json()
                        oj_submission_id = result.get('id')

                        # 设置对应字段
                        if repo_type == 'basic':
                            submission.basic_submission_id = oj_submission_id
                        elif repo_type == 'book':
                            if i == 0:
                                submission.book_submission_id = oj_submission_id
                            else:
                                submission.book_second_submission_id = oj_submission_id
                        elif repo_type == 'icpc':
                            submission.icpc_submission_id = oj_submission_id
                        elif repo_type == 'python':
                            submission.python_submission_id = oj_submission_id
                        elif repo_type == 'ticket':
                            submission.ticket_submission_id = oj_submission_id

                        submission.details += f"\n{repo_type.capitalize()}仓库提交到题目{problem_id}，OJ提交ID: {oj_submission_id}"
                        db.session.commit()
                    else:
                        submission.details += f"\n{repo_type.capitalize()}仓库提交到题目{problem_id}失败: {response.status_code} - {response.text}"
                        db.session.commit()

                    # 避免API请求过快
                    time.sleep(2)

        # 启动监控线程，监控评测状态
        threading.Thread(
            target=check_submission_status,
            args=(submission.id,),
            daemon=True
        ).start()

    except Exception as e:
        try:
            submission = Submission.query.get(submission_id)
            if submission:
                submission.details = f"提交过程中出错: {str(e)}"
                db.session.commit()
        except:
            print(f"[严重错误] 无法更新数据库: {e}")
# routes


@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 30

    models_query = Model.query.order_by(
        db.func.coalesce(
            db.func.max(Submission.score),
            0
        ).desc()
    ).join(
        Submission,
        Model.id == Submission.model_id,
        isouter=True
    ).group_by(Model.id)

    # 分页
    pagination = models_query.paginate(page=page, per_page=per_page)
    models = pagination.items

    # 获取统计信息
    models_count = Model.query.count()
    submissions_count = Submission.query.count()
    top_score = db.session.query(db.func.max(Submission.score)).scalar() or 0

    return render_template(
        'index.html',
        models=models,
        has_more_models=pagination.has_next,
        models_count=models_count,
        submissions_count=submissions_count,
        top_score=top_score,
        Submission=Submission,  # 传递模型类给模板
        db=db  # 传递db对象给模板以便使用func等功能
    )


@app.route('/api/models')
def api_models():
    page = request.args.get('page', 1, type=int)
    per_page = 30

    # 获取排序后的模型列表
    models_query = Model.query.order_by(
        db.func.coalesce(
            db.func.max(Submission.score),
            0
        ).desc()
    ).join(
        Submission,
        Model.id == Submission.model_id,
        isouter=True
    ).group_by(Model.id)

    # 分页
    pagination = models_query.paginate(page=page, per_page=per_page)
    models = pagination.items

    # 准备JSON响应
    models_data = []
    for model in models:
        submissions = model.submission.all()
        scores = [s.score for s in submissions if s.score is not None]

        models_data.append({
            'id': model.id,
            'name': model.name,
            'organization': model.organization,  # 添加组织信息
            'description': model.description,
            'submissions_count': len(submissions),
            'avg_score': sum(scores) / len(scores) if scores else 0,
            'best_score': max(scores) if scores else 0,
            'last_submit': submissions[0].submission_time.strftime('%Y-%m-%d %H:%M') if submissions else None
        })

    return jsonify({
        'models': models_data,
        'has_more': pagination.has_next
    })


UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    models = Model.query.all()

    # 获取URL中传递的model_id参数，用于预选模型
    selected_model_id = request.args.get('model_id', type=int)

    if request.method == 'POST':
        model_id = request.form.get('model_id', type=int)
        zip_file = request.files.get('zip_file')

        if not model_id or not zip_file:
            flash('模型ID和ZIP文件都是必填项', 'error')
            recent_submissions = Submission.query.order_by(
                Submission.submission_time.desc()).limit(10).all()
            return render_template('submit.html', submissions=recent_submissions, models=models, selected_model_id=selected_model_id)

        model = Model.query.get(model_id)
        if not model:
            flash('找不到指定的模型', 'error')
            recent_submissions = Submission.query.order_by(
                Submission.submission_time.desc()).limit(10).all()
            return render_template('submit.html', submissions=recent_submissions, models=models, selected_model_id=selected_model_id)

        # 保存 zip 文件
        filename = secure_filename(zip_file.filename)
        saved_path = os.path.join('uploads', filename)
        zip_file.save(saved_path)

        submission = Submission(
            model_id=model_id,
            problem_id=0,  # 设置一个默认值，因为我们不再使用单一的问题ID
            details=f"使用模型 {model.name}，文件 {filename} 正在处理中..."
        )
        db.session.add(submission)
        db.session.commit()

        try:
            threading.Thread(
                target=process_git_submission,
                args=(submission.id, model.id, saved_path),
                daemon=True
            ).start()

            flash('提交成功！系统正在处理您的请求...', 'success')
            # 跳转到提交详情页面
            return redirect(url_for('submission_detail', submission_id=submission.id))

        except Exception as e:
            db.session.rollback()
            flash(f'提交处理过程中出错: {str(e)}', 'error')
            return redirect(url_for('submit'))

    recent_submissions = Submission.query.order_by(
        Submission.submission_time.desc()).limit(10).all()
    return render_template('submit.html', submissions=recent_submissions, models=models, selected_model_id=selected_model_id)


@app.route('/process_submission', methods=['POST'])
def process_submission():
    problem_id = request.form.get('problem_id', type=int)
    model_name = request.form.get('model_name')

    if not problem_id or not model_name:
        return jsonify({'error': 'problem_id or model_name is missing.'}), 400

    model = get_model_by_name(model_name)
    if not model:
        return jsonify({'error': 'Model not found.'}), 404

    submission = Submission(model_id=model.id, score=None,
                            details=f"Submission for problem {problem_id} of {model_name}.")
    db.session.add(submission)
    db.session.commit()

    flash("Submission received. Thank you for your contribution!")
    return redirect(url_for('submission_detail', submission_id=submission.id))


@app.route('/model/<int:model_id>')
def model_detail(model_id):
    page = request.args.get('page', 1, type=int)
    per_page = 20  # 每页显示20条提交记录

    model = Model.query.get_or_404(model_id)

    # 获取该模型的最高分提交
    best_submission = Submission.query.filter_by(
        model_id=model_id).order_by(Submission.score.desc()).first()

    # 分页获取该模型的所有提交
    pagination = model.submission.order_by(
        Submission.submission_time.desc()
    ).paginate(page=page, per_page=per_page)

    submissions = pagination.items

    return render_template(
        'model_detail.html',
        model=model,
        submissions=submissions,
        best_submission=best_submission,
        pagination=pagination
    )


@app.route('/submission/<int:submission_id>')
def submission_detail(submission_id):
    submission = Submission.query.get_or_404(submission_id)

    # 获取最新评测状态
    update_submission_status(submission)

    return render_template('submission_detail.html', submission=submission)


@app.route('/add_model', methods=['GET', 'POST'])
def add_model():
    if request.method == 'POST':
        name = request.form.get('name')
        organization = request.form.get('organization', '')
        description = request.form.get('description', '')

        if not name:
            flash('模型名称不能为空', 'error')
            return redirect(url_for('add_model'))

        # 检查模型名称是否已存在
        existing_model = get_model_by_name(name)
        if existing_model:
            flash('该模型名称已存在', 'error')
            return redirect(url_for('add_model'))

        # 创建新模型
        try:
            model = create_model(name, description, organization)
            flash(f'模型 "{name}" 添加成功', 'success')
            return redirect(url_for('model_detail', model_id=model.id))
        except Exception as e:
            flash(f'添加模型失败: {str(e)}', 'error')
            return redirect(url_for('add_model'))

    # 获取最近添加的模型
    recent_models = Model.query.order_by(Model.id.desc()).limit(5).all()
    # 获取所有模型用于删除操作
    all_models = Model.query.order_by(Model.name).all()

    return render_template('add_model.html', recent_models=recent_models, all_models=all_models)


@app.route('/delete_model', methods=['POST'])
def delete_model():
    delete_model_id = request.form.get('delete_model_id', type=int)
    if not delete_model_id:
        flash('请选择要删除的模型', 'error')
        return redirect(url_for('add_model'))

    model = Model.query.get(delete_model_id)
    if not model:
        flash('找不到指定的模型', 'error')
        return redirect(url_for('add_model'))

    try:
        model_name = model.name
        # 删除该模型的所有提交记录
        Submission.query.filter_by(model_id=delete_model_id).delete()

        # 删除模型
        db.session.delete(model)
        db.session.commit()

        flash(f'模型 "{model_name}" 及其所有提交记录已成功删除', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除模型失败: {str(e)}', 'error')

    return redirect(url_for('add_model'))   


@app.cli.command("initdb")
def initdb_command():
    click.echo("Initializing database...")
    db.drop_all()
    db.create_all()
    if not get_model_by_name("test"):
        create_model("test", "Empty test model")
    click.echo("Database initialization complete!")

if __name__ == '__main__':
    app.run(debug=True)
