# Spinnaker SDK & Python 연동

본 튜토리얼은 PySpin모듈을 사용하기에 PySpin과 연동이 되는 파이썬 버전을 사용함.

## 1. Spinnaker SDK Download

* [Spinnaker SDK Download](https://www.teledynevisionsolutions.com/ko-kr/products/spinnaker-sdk/?model=Spinnaker%20SDK&vertical=machine%20vision&segment=iis) 로그인 후 아래 두가지 파일 다운로드

  **Sinnaker 4.2 for Window**

  bit는 본인 컴퓨터에 맞게 32 or 64 선택하여 설치

  * Status: Feature / Description: 64-bit Windows Full
    * .exe 실행 및 설치
  * Status: Feature / Description: 64-bit Python3.8
    * 압축 풀기



## 2. Create New environment & Module, package dowload

* Create New environment
  * conda create -n <envname> python=3.8
* Neccesary module Download
  * pip install matplotlib
  * pip install keyboard
  * pip install PySpin
* Necessary Python package설치
  * conda activate envname
  * cd .whl파일 존재 경로
  * python -m pip install .whl file

## 3. Check PySpin

* write below code sequencially
  * conda activate envname
  * python > import PySpin > system = PySpin.System.GetInstance()

