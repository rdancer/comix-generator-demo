OPENAI_API_KEY=$(shell cat ~/OPENAI_API_KEY-comix-generator.rdancer.org.txt)

PORT=5000

.PHONY: run
run: kill_all_on_port
		bash script/start "$(OPENAI_API_KEY)"

.PHONY: kill_all_on_port
kill_all_on_port:
	kill -9 `lsof -t -i :$(PORT)` 2>/dev/null || :
