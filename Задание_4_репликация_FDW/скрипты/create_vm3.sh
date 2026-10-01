#!/usr/bin/env bash
# Учебное создание 3-й ВМ (клон) для практики РБД / задания 4.
# Запускать на ХОСТЕ (Pop!_OS), не внутри ВМ.
#
#   chmod +x scripts/create_vm3.sh
#   ./scripts/create_vm3.sh
#
set -euo pipefail

CONNECT="qemu:///system"
SRC="${SRC_VM:-ubuntu24.04-2}"          # источник (лучше выключенный)
NAME="${NEW_VM:-ubuntu24.04-11}"
DISK="${DISK_PATH:-/var/lib/libvirt/images/${NAME}.qcow2}"

echo "=== Проверка ==="
virsh --connect "$CONNECT" list --all
echo

if virsh --connect "$CONNECT" dominfo "$NAME" &>/dev/null; then
  echo "ВМ '$NAME' уже существует. Удалить и создать заново?"
  echo "  virsh --connect $CONNECT destroy $NAME || true"
  echo "  virsh --connect $CONNECT undefine $NAME --remove-all-storage"
  exit 1
fi

STATE=$(virsh --connect "$CONNECT" domstate "$SRC" 2>/dev/null || echo missing)
if [[ "$STATE" == "missing" ]]; then
  echo "Нет исходной ВМ: $SRC"
  exit 1
fi
if [[ "$STATE" == "running" ]]; then
  echo "Исходная ВМ '$SRC' запущена. Для чистого клона выключите её:"
  echo "  virsh --connect $CONNECT shutdown $SRC"
  echo "или в Virtual Machine Manager → Shut Down."
  exit 1
fi

echo "=== Клонирование $SRC → $NAME ==="
echo "Диск: $DISK"
sudo virt-clone \
  --connect "$CONNECT" \
  --original "$SRC" \
  --name "$NAME" \
  --file "$DISK"

echo
echo "=== Старт $NAME ==="
virsh --connect "$CONNECT" start "$NAME"

echo
echo "Подождите ~20–40 с (DHCP), затем:"
echo "  virsh --connect $CONNECT domifaddr $NAME"
echo "  # или внутри консоли ВМ: ip -4 a"
echo
echo "Дальше зайдите по SSH (логин/пароль как на VM2: db1 / 1) и выполните:"
echo "  sudo hostnamectl set-hostname db-server-11"
echo "  # чтобы не конфликтовать с клоном:"
echo "  sudo rm -f /etc/machine-id"
echo "  sudo systemd-machine-id-setup"
echo "  sudo reboot"
echo
echo "После reboot узнайте IP и добавьте в /etc/hosts на хосте, например:"
echo "  192.168.122.61  db-server-11"
echo
echo "Готово. Список ВМ:"
virsh --connect "$CONNECT" list --all
