run_gpsd:
	-@sudo killall gpsd
	@sudo systemctl stop gpsd.socket
	@sudo systemctl disable gpsd.socket
	@sudo gpsd /dev/serial0 -F /var/run/gpsd.sock
	@echo "gpsd running"

debug: run_gpsd
	@cgps -s

active_processes:
	@ps aux | grep python

install_required:
	@sudo apt-get install gpsd gpsd-clients
	@python -m pip install gps
	@echo "python packages installed"

install_pisugar_manager:
	@curl http://cdn.pisugar.com/release/pisugar-power-manager.sh | sudo bash
	@echo "pisugar manager installed"

install: install_required install_pisugar_manager
	@echo "all packages installed"

pisugar_setup_button_actions:
	@sudo sed -i 's/"single_tap_enable": false/"single_tap_enable": true/g' /etc/pisugar-server/config.json
	@sudo sed -i 's/"double_tap_enable": false/"double_tap_enable": true/g' /etc/pisugar-server/config.json
	@sudo sed -i 's/"long_tap_enable": false/"long_tap_enable": true/g' /etc/pisugar-server/config.json

	@sudo sed -i 's/"single_tap_shell": ""/"single_tap_shell": "cd \/home\/user \&\& make"/g' /etc/pisugar-server/config.json

	@sudo systemctl restart pisugar-server
	@echo "button actions setup"

pisugar_config:
	@cat /etc/pisugar-server/config.json

device_name=GPSD
usb_set_name:
	@sudo dosfslabel /boot/usb-drive.img $(device_name)
	@echo "drive name set to $(device_name)"

systemctl_configure:
	@sudo cp gpsd.service /etc/systemd/system/gpsd.service
	@sudo systemctl daemon-reload
	@echo "systemctl configured"

systemctl_logs:
	@sudo journalctl -u gpsd.service -f

systemctl_disable:
	@sudo systemctl stop gpsd.service
	@sudo systemctl disable gpsd.service
	@echo "systemctl disabled"

systemctl_enable:
	@sudo systemctl enable gpsd.service
	@sudo systemctl start gpsd.service
	@echo "systemctl enabled"