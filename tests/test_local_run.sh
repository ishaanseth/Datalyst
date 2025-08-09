
#!/usr/bin/env bash
set -e
# simple test: run uvicorn in background and send a sample questions.txt
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --host 127.0.0.1 &
UV_PID=$!
sleep 2
echo "questions: read https://en.wikipedia.org/wiki/List_of_highest-grossing_films" > q.txt
curl -F "questions=@q.txt" http://127.0.0.1:8000/api/ -v
kill $UV_PID
