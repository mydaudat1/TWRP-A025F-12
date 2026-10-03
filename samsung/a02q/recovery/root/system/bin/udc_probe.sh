#!/system/bin/sh
# 1) đặt dwc3-msm sang peripheral  2) tìm UDC thật  3) tạo /dev/mtp_usb -> node misc MTP của kernel Samsung
# Chỉ setprop khi giá trị thay đổi: setprop cùng giá trị vẫn kích hoạt lại trigger
# `on property:...` và làm gadget bị rebind (MTP rớt kết nối).
i=0
UDC_OK=; MTP_OK=
while [ $i -lt 150 ]; do
  for m in /sys/bus/platform/devices/*ssusb*/mode; do
    [ -w "$m" ] && [ "$(cat $m 2>/dev/null)" != "peripheral" ] && echo peripheral > "$m" 2>/dev/null
  done
  if [ -z "$UDC_OK" ]; then
    u=$(ls /sys/class/udc 2>/dev/null | head -n 1)
    if [ -n "$u" ]; then
      [ "$(getprop sys.usb.controller)" != "$u" ] && setprop sys.usb.controller "$u"
      UDC_OK=1
    fi
  fi
  if [ -z "$MTP_OK" ]; then
    for n in $(ls /sys/class/misc 2>/dev/null | grep -i mtp); do
      if [ -c "/dev/$n" ]; then
        ln -sf "/dev/$n" /dev/mtp_usb && chmod 0660 "/dev/$n" && MTP_OK=1 && break
      fi
    done
  fi
  [ -n "$UDC_OK" ] && [ -n "$MTP_OK" ] && exit 0
  i=$((i+1)); sleep 0.2
done
log -t udc_probe "timeout: udc='$UDC_OK' mtp='$MTP_OK'" 2>/dev/null
exit 0
