FROM php:8.2-apache

RUN docker-php-ext-install curl 2>/dev/null || true

COPY index.php /var/www/html/index.php

RUN a2enmod rewrite
