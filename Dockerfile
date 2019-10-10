FROM python:alpine
RUN pip install requests
ADD crontab.txt /crontab.txt
ADD amz_inv_updtr.py /amz_inv_updtr.py
COPY entry.sh /entry.sh
RUN chmod 755 /amz_inv_updtr.py /entry.sh
RUN /usr/bin/crontab /crontab.txt
EXPOSE 80
CMD ["/entry.sh"]
