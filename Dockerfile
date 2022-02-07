FROM python:3
MAINTAINER Iaroslav Omelianenko <iaroslav@comet.ml>

WORKDIR /usr/src/app

# install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copy files
COPY oscontainer oscontainer
COPY main.py .

CMD [ "python", "./main.py" ]