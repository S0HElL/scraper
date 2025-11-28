import json

def fix_ids():
    with open('professors.jsonl', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    for i, line in enumerate(lines, start=1):
        data = json.loads(line.strip())
        data['id'] = i
        fixed_lines.append(json.dumps(data, ensure_ascii=False))

    with open('professors.jsonl', 'w', encoding='utf-8') as f:
        for line in fixed_lines:
            f.write(line + '\n')

if __name__ == '__main__':
    fix_ids()