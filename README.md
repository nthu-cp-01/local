# local

## 0. 設定AWS Infra
- 執行Makefile裡的terraform腳本:
```bash
make setup
```
- 結果會輸出iot_endpoint跟`id.pem`(private key), `certificate.pem`等檔案。

## 1. 安裝conda
- https://www.anaconda.com/docs/getting-started/miniconda/install#quickstart-install-instructions

## 2. 建立conda環境:
```bash
conda env create -f environment.yaml
conda activate local
```

## 3. 執行測試腳本
- 記得先去console裡開啟測試用的mqtt client subscribe `test/topic`:
```bash
make test-mqtt <前面拿到的iot_endpoint>
```
