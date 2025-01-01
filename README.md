### 
```
docker build -t ai-novelist .

export DEEPSEEK_API_KEY=XXXXXXXXXX

docker run -it --rm -v $(pwd):/workspace -p 8888:8888 ai-novelist bash

python prepare.py 
task5/AI-Scientist/data/novel/novel.txt => 生成




```