### 
```
git clone https://github.com/miyaki-mac/AI-Novelist.git

cd AI-Novelist/

docker build -t ai-novelist . 

docker run -it --rm -e DEEPSEEK_API_KEY={YOUR_API_KEY} -v .:/workspace -p 8888:8888 ai-novelist bash


python data/novel/prepare.py

docker build -t ai-novelist .

export DEEPSEEK_API_KEY=XXXXXXXXXX

docker run -it --rm -v $(pwd):/workspace -p 8888:8888 ai-novelist bash

python prepare.py 
task5/AI-Scientist/data/novel/novel.txt => 生成




```