import v2v
import json

manus = json.loads(open("script_1.json").read())
film = v2v.Film(manus, "the_outfile.mp4")
film.start()
