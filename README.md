# Learned Leage

Showcase the amazing variety of [Learned League](https://learnedleague.com) flags.

## Getting Started

The generate_html.py python script will generate an index.html file and players.js file that can be use to display Learned League member's flags.

The .htaccess file is needed to translate the links in the menu into the proxied index.html targets.

### Prerequisites

Pipenv:
A pipenv pipfile is included with prerequisites.

This can be used like...

```
pipenv install
```

### Installing
Change the member name and password in logindata.ini.example and rename to logindata.ini.

Run the python script in the folder where this is cloned.

```
pipenv run python generate_html.py
```

Fix any errors and repeat. ;)

## Deployment
Copy the ll folder to your webhost.
## Built With

This script started off based on [llama_slobbber](https://github.com/wusui/llama_slobber). Kudos, wsui.

## Contributing

Pull request welcomed.

## Versioning

## Authors

[WyattW](https://learnedleague.com/profiles.php?34441)

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details
