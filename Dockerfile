#
# The line below states we will base our new image on the Latest Official Ubuntu 
FROM ubuntu:latest
 
#
# Identify the maintainer of an image
LABEL maintainer="tan.dovan@hpe.com"
 
#
# Update the image to the latest packages
RUN apt-get update && apt-get upgrade -y
 
#
# Install httpd
RUN apt-get install httpd -y
 
#
# Expose port 80
EXPOSE 80

#
# start httpd within our Container
CMD ["httpd", "-g", "daemon off;"]

