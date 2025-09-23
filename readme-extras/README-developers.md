# BookForge Studio - Developers README

## Project structure

* backend - main fastapi server python code
	* core - various fastapi routers and other python code for the main server functionality
	* models - python code for the main server which is specific to each audio model
	* steps - small, dynamically loaded "steps" of a text workflow which do individual tasks and
		can be chained together. New steps can be added and ideally, users may make their own
		custom steps and throw them in this folder.
	* text_workflows - code related to converting text, csv's, etc. into BFS script files.
* files - this folder is designed to include all the *user's files,* for example uploaded audio,
	scripts, etc. 
	* After initial setup the 'files' folder will come preloaded with various voice clone clips,
		actors, and scripts as "starter project" files to demonstrate functionality.
* frontend - react typescript frontend source code.
* frontend-build - a built version of the frontend, served by the main server for end users.
* models - code related to individual ai model microservices, including their python dependencies,
	and a tiny fastapi server just for hosting the model. 
* app.py - python code to run the main server
* install.bat, Makefile - entry point for windows and unix users
* run_model.py - python file used when running an ai model microservice.

## Running the Full App in Development Mode

We provide here the unix `make` commands as well as the direct python/node commands. 

When actively developing the frontend, you'll want to run both the React development server and the 
backend in development mode:

1. **Start the backend in development mode (`make local` in unix):**

	`make local`

	

	```bash
	python app.py --dev
	```

2. **Start the React development server (`make frontend` in unix):**
	```bash
	cd frontend
	npm start
	```

3. **Start an AI service (`make <name>-service`, or `make mock-service`, in unix):**
	```bash
	python run_model.py <name>
	```
	

4. **Access the application:**

   http://localhost:3000 (with hot reload)

## Features as Additional Makefile Commands

This repo has some extra features for developers. In no particular order:

* `make local-testing-ui` and `make mock-service` allow for people without graphics cards to 
	mock inference locally by copying voice clone files instead of actually performing inference.
	This is very useful for developing features on a weak computer before testing them out on
	a beefier machine. These two commands in combination with `make frontend` should allow for 
	development and manual testing of most functionality on a decent computer without running
	the real AI models. (Note that whisper is still in the main server, which can take up some
	resources -- it might be a good idea to change this later.)
* `make generate-ts-types` Generates typescript type definitions based on openapi schema provided
	by python server. This requires the fastapi server to be running.
* `make test` runs two suites of tests; the first is just a concurrency test which relies on the
	'mock service' to be running with a 3 second simulated delay; the second is a longer suite of 
	other tests which restart 'mock service' with a faster simulated delay to run quicker.
* `make local-expose-host`, `make main-expose-host` and `make frontend-expose-host` are all for LAN
	debugging, which allows for a user to test Windows Edge against another laptop on the same
	LAN network (for example). 
