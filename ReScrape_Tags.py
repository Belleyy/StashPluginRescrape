import log
import sys
import json
import os
from shutil import copyfile
from stash_interface import StashInterface


def main():
    json_input = read_json_input()
    output = {}
    run(json_input, output)
    out = json.dumps(output)
    print(out + "\n")


def read_json_input():
    json_input = sys.stdin.read()
    return json.loads(json_input)


def run(json_input, output):
    mode_arg = json_input['args']['mode']
    try:
        client = StashInterface(json_input["server_connection"])
        # Personnal things
        if mode_arg == "JAV":
            findScene(client, "1. JAV")
        if mode_arg == "Anime":
            findScene(client, "1. Anime")
        if mode_arg == "Western":
            findScene(client, "1. Western")
    except Exception:
        raise
    output["output"] = "ok"


def findScene(client, tags_name):
    backupDB(client)

    log.LogDebug(f"Searching scenes...")

    tags_id = client.findTagIdWithName(tags_name)
    log.LogDebug("Your tag ID:" + str(tags_id))

    scenes = client.findScenesByTags([tags_id])
    log.LogDebug("Nbr Scenes with this tag:" + str(len(scenes)))

    # Get the ID of the tags writed by this plugin
    pluginsTagsID = get_scrape_tag(client)
    for scene_fromTags in scenes:
        log.LogDebug("Scene:" + str(scene_fromTags))
        # Scene need to have a url set
        if scene_fromTags['url'] == None:
            continue
        # Only wanted to use the scraper Javlibrary
        if 'javlibrary' not in scene_fromTags['url']:
            continue
        # get_scrape_tag only give URL and ID so using getSceneById to get more information
        scene = client.getSceneById(scene_fromTags['id'])

        # Current tags present in scene
        AlreadyWatch=0
        sceneTags = []
        for tags in scene.get('tags'):
            if tags['id'] == pluginsTagsID:
                log.LogDebug("Already watched")
                AlreadyWatch=1
                break
            else:
                sceneTags.append(tags['id'])
        if AlreadyWatch == 1:
            continue
        # I guess URL is useless since check above
        if scene['url'] != None and scene['tags'] != None:
            # Scraping scene (What happend if the URL don't have scraper ?)
            scrapedData = client.scrapeSceneURL(scene['url'])
            if scrapedData == None:
                log.LogDebug("Error when scraping ?")
                continue
            scrapedTags = []
            if scrapedData['tags'] == None:
                log.LogDebug("No tags from Scraping")
                continue
            for tags in scrapedData['tags']:
                # Only take tags that already exist in Database
                if tags['stored_id'] == None:
                    continue
                scrapedTags.append(tags['stored_id'])
            # Probably useless ?
            if not scrapedTags:
                log.LogDebug("No tags from Scraping")
                continue

            # Compare
            log.LogDebug("Current Tags:" + str(sceneTags))
            log.LogDebug("Scraped Tags:" + str(scrapedTags))
            # Remove duplicate
            unique_Tags = list(set(sceneTags + scrapedTags))
            log.LogDebug("Unique Tags:" + str(unique_Tags))
            # Look for tags not in the current tag list.
            new_tags = []
            for tags in unique_Tags:
                if tags in sceneTags:
                    continue
                else:
                    new_tags.append(tags)
            if not new_tags:
                log.LogDebug("No new tags")
            else:
                log.LogDebug("New Tags:" + str(new_tags))

            # Get all data needed for update (Stolen from niemands plugins)
            scene_data = {
                'id': scene.get('id'),
                'url': scene.get('url'),
                'title': scene.get('title')
            }

            if scrapedData.get('details'):
                scene_data['details'] = scrapedData.get('details')

            performer_ids = []
            for p in scene.get('performers'):
                performer_ids.append(p.get('id'))
            scene_data['performer_ids'] = performer_ids

            if scene.get('studio'):
                scene_data['studio_id'] = scene.get('studio').get('id')

            if scene.get('gallery'):
                scene_data['gallery_id'] = scene.get('gallery').get('id')

            if scene.get('rating'):
                scene_data['rating'] = scene.get('rating')

            if not new_tags:
                # No new tags but we still put our custom tags to don't scan it again.
                tag_ids = []
                for t in scene.get('tags'):
                    tag_ids.append(t.get('id'))
                # Putting our custom tag
                tag_ids.append(pluginsTagsID)
                scene_data['tag_ids'] = tag_ids
            else:
                new_tags.append(pluginsTagsID)
                scene_data['tag_ids'] = new_tags + sceneTags
                log.LogDebug("Updated scene: " + str(scene.get('title')))
            client.updateScene(scene_data)
            # break

def get_scrape_tag(client):
    tag_name = "00. ReScrape"
    tag_id = client.findTagIdWithName(tag_name)
    if tag_id is not None:
        return tag_id
    else:
        client.createTagWithName(tag_name)
        tag_id = client.findTagIdWithName(tag_name)
        return tag_id


def backupDB(client):
    configuration = client.getConfiguration()
    dbPath = configuration['general']['databasePath']
    dbName = os.path.basename(dbPath) + "_ReScrape.sqlite"
    dbDir = os.path.dirname(dbPath)  # Get filename
    newPath=dbDir + "\\" + dbName
    log.LogDebug("Making backup of your database...")
    copyfile(dbPath, newPath)

main()
