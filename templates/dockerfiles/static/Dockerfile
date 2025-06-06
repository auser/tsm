FROM nginx:alpine

COPY ./dockerfiles/static/robots.txt /usr/share/nginx/html/robots.txt

RUN echo 'server { listen 8081; location / { root /usr/share/nginx/html; } }' > /etc/nginx/conf.d/default.conf

EXPOSE 8081
