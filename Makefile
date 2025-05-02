setup:
	terraform -chdir=infra init
	terraform -chdir=infra apply

test-mqtt:
	python basic_mqtt.py --endpoint $(filter-out $@,$(MAKECMDGOALS)) --cert certificate.pem --key id.pem
