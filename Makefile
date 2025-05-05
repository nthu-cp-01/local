setup:
	terraform -chdir=infra init
	terraform -chdir=infra apply

test-mqtt:
	python basic_mqtt.py --endpoint $(filter-out $@,$(MAKECMDGOALS)) --cert certificate.pem --key id.pem

test-shadow:
	python shadow.py --endpoint $(filter-out $@,$(MAKECMDGOALS)) --cert certificate.pem --key id.pem --thing_name jetson-xavier-nx
receive-shadow:
	python receive.py --endpoint $(filter-out $@,$(MAKECMDGOALS)) --cert certificate.pem --key id.pem --thing_name jetson-xavier-nx
