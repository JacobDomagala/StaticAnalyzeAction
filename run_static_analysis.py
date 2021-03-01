import argparse
from github import Github
import os

# Input variables from Github action
GITHUB_TOKEN = os.getenv('INPUT_GITHUB_TOKEN')
PR_NUM = int(os.getenv('INPUT_PR_NUM'))
WORK_DIR = os.getenv('GITHUB_WORKSPACE')
REPO_NAME = os.getenv('INPUT_REPO')
SHA = os.getenv('GITHUB_SHA')
COMMENT_TITLE = os.getenv('INPUT_COMMENT_TITLE')

# Max characters per comment - 65536
# Make some room for HTML tags and error message
MAX_CHAR_COUNT_REACHED = '!Maximum character count per GitHub comment has been reached! Not all warnings/errors has been parsed!'
COMMENT_MAX_SIZE = 65000
current_comment_length = 0

def check_for_char_limit(incoming_line):
    global current_comment_length
    return (current_comment_length + len(incoming_line)) <= COMMENT_MAX_SIZE

def create_comment_for_output(tool_output, prefix):
    global current_comment_length
    output_string = ''
    for line in tool_output:
        if line.startswith(prefix):
            line = line.replace(prefix, "")
            file_path_end_idx = line.index(':')
            file_path = line[:file_path_end_idx]
            line = line[file_path_end_idx+1:]
            file_line_start = int(line[:line.index(':')])
            file_line_end = file_line_start + 5
            description = f"\n```diff\n!Line: {file_line_start} - {line[line.index(' ')+1:]}```\n"

            new_line = f'\nhttps://github.com/{REPO_NAME}/blob/{SHA}/{file_path}#L{file_line_start}-L{file_line_end} {description} </br>\n'
            if check_for_char_limit(new_line):
                output_string += new_line
                current_comment_length += len(new_line)
            else:
                current_comment_length = COMMENT_MAX_SIZE
                return output_string

    return output_string

# Get cppcheck and clang-tidy files
parser = argparse.ArgumentParser()
parser.add_argument('-cc', '--cppcheck', help='Output file name for cppcheck', required=True)
parser.add_argument('-ct', '--clangtidy', help='Output file name for clang-tidy', required=True)
cppcheck_file_name = parser.parse_args().cppcheck
clangtidy_file_name = parser.parse_args().clangtidy

cppcheck_content = ''
with open(cppcheck_file_name, 'r') as file:
    cppcheck_content = file.readlines()

clang_tidy_content = ''
with open(clangtidy_file_name, 'r') as file:
    clang_tidy_content = file.readlines()

line_prefix = f'{WORK_DIR}'

cppcheck_comment = create_comment_for_output(cppcheck_content, line_prefix)
clang_tidy_comment = create_comment_for_output(clang_tidy_content, line_prefix)

full_comment_body = f'<b><h2> {COMMENT_TITLE} </h2></b> </br>'\
    f'<details> <summary> <b>CPPCHECK</b> </summary> </br>'\
    f'{cppcheck_comment} </details></br>'\
    f'<details> <summary> <b>CLANG-TIDY</b> </summary> </br>'\
    f'{clang_tidy_comment} </details></br>\n'

if current_comment_length == COMMENT_MAX_SIZE:
    full_comment_body += f'\n```diff\n{MAX_CHAR_COUNT_REACHED}\n```'

print(f'Repo={REPO_NAME} pr_num={PR_NUM} comment_title={COMMENT_TITLE}')

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)
pr = repo.get_pull(PR_NUM)

comments = pr.get_issue_comments()
found_id = -1
comment_to_edit = None
for comment in comments:
    if (comment.user.login == 'github-actions[bot]') and (COMMENT_TITLE in comment.body):
        found_id = comment.id
        comment_to_edit = comment
        break

if found_id != -1:
    comment_to_edit.edit(body = full_comment_body)
else:
    pr.create_issue_comment(body = full_comment_body)

