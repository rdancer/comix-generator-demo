OPENAI_API_KEY=$(shell cat ~/OPENAI_API_KEY-rdancer.txt)

run:
		bash script/start "$(OPENAI_API_KEY)"