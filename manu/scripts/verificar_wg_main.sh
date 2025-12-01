#!/bin/bash
# Script para verificar la configuración de wg-main
# Ejecutar en el servidor Ubuntu para obtener la IP del servidor en la VPN

echo "Verificando configuración de wg-main..."
echo ""

# Ver la IP del servidor en la interfaz wg-main
echo "1. IP del servidor en la VPN (wg-main):"
sudo wg show wg-main | grep -A 1 "interface" | grep -v "interface" || ip addr show wg-main | grep "inet "

echo ""
echo "2. Verificar archivo de configuración de wg-main:"
if [ -f "/etc/wireguard/wg-main.conf" ]; then
    echo "Archivo encontrado: /etc/wireguard/wg-main.conf"
    sudo grep -i "Address" /etc/wireguard/wg-main.conf
else
    echo "Archivo /etc/wireguard/wg-main.conf no existe"
    echo "Verificando si wg-main se creó desde wg0.conf..."
fi

echo ""
echo "3. Información completa de wg-main:"
sudo wg show wg-main

