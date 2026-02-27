
import requests
response = requests.get('http://127.0.0.1:8000/voting/nominate-to-unwind-students-youth/')
with open('test_html.txt', 'w', encoding='utf-8') as f:
    f.write(response.text)
print('HTML saved to test_html.txt')
