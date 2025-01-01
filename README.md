# Title
AI-Novelist

# Overview
The system automatically generates spin-off stories based on a specified novel.
The AI creates multiple settings and plots, refines them, and writes the novel while continuously improving the content.

# Usage
## Clone the repository:
```
git clone https://github.com/miyaki-mac/AI-Novelist.git
cd AI-Novelist/
```
## Docker Build & Run:
```
docker build -t ai-novelist . 
docker run -it --rm 
    -e DEEPSEEK_API_KEY={YOUR_API_KEY} 
    -v .:/workspace ai-novelist bash
```

## Preparation:
```
python data/novel/prepare.py
    -u {青空文庫のテキストファイル(ルビあり)zipデータ}（default:走れメロス）

cd templates/fascinating_spin_off/
python experiment.py 
```

## Start Writing:
```
cd ../../
python launch_novelist.py --num-ideas 2
```

# Examples of Output:
太宰 治「走れメロス」のスピンオフ作品  
※参照先：青空文庫 走れメロス（[URL](https://www.aozora.gr.jp/cards/000035/card1567.html#download)）  
OUTPUT:[Spin-off novel](examples/走れメロス_Spin-off.pdf)
