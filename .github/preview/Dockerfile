# Web preview image: the multithreaded web build behind nginx. The build context is made by
# the "Preview" workflow: site/ (the install directory of the web build), nginx.conf and
# preview-headers.conf.
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY preview-headers.conf /etc/nginx/preview-headers.conf
COPY site/ /usr/share/nginx/html/
