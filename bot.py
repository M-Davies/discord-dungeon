###
# Project: oghma
# Author: shadowedlucario
# https://github.com/shadowedlucario
###

import os
import requests
import json
import discord
import logging
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()

### GLOBALS ###
botName = "Oghma"
TOKEN = os.getenv('BOT_TOKEN')
bot = commands.Bot(command_prefix='?')
client = discord.Client()
partialMatch = False

# Set up logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

###
# FUNC NAME: searchResponse
# FUNC DESC: Searches the API response for the user input. Returns None if nothing was found
# FUNC TYPE: Function
###
def searchResponse(responseResults, filteredInput):
    global partialMatch
    match = None
    for entity in responseResults:

        # Documents don't have a name attribute
        if "title" in entity:

            # Has to be in it's own "if" to avoid KeyErrors
            if entity["title"].replace(" ", "").lower() == filteredInput:
                match = entity
                break

            # Now try partially matching the entity (i.e. bluedragon will match adultbluedragon here)
            if filteredInput in entity["title"].replace(" ", "").lower():
                partialMatch = True

                match = entity
                break
        
        elif "name" in entity:
            
            if entity["name"].replace(" ", "").lower() == filteredInput:
                match = entity
                break

            if filteredInput in entity["name"].replace(" ", "").lower():
                partialMatch = True

                match = entity
                break

        else: match = "UNKNOWN"

    return match

###
# FUNC NAME: requestAPI
# FUNC DESC: Queries the API. 
# FUNC TYPE: Function
###
def requestAPI(query, filteredInput, wideSearch):

    # API Request
    request = requests.get(query)

    # Return code if not successfull
    if request.status_code != 200: return {"code": request.status_code, "query": query}

    # Iterate through the results
    output = searchResponse(request.json()["results"], filteredInput)

    if output == None: return output

    elif output == "UNKNOWN": return "UNKNOWN"

    # Find resource object if coming from search endpoint
    elif wideSearch == True:

        # Request resource using the first word of the name to filter results
        route = output["route"]

        if "title" in output:
            resourceRequest = requests.get(
                "https://api.open5e.com/{}?format=json&limit=10000&search={}"
                .format(
                    route,
                    output["title"].split()[0]
                )
            )
        else:
            resourceRequest = requests.get(
                "https://api.open5e.com/{}?format=json&limit=10000&search={}"
                .format(
                    route,
                    output["name"].split()[0]
                )
            )

        # Return code if not successfull
        if resourceRequest.status_code != 200: 
            return {
                "code": resourceRequest.status_code,
                "query": "https://api.open5e.com/{}?format=json&limit=10000&search={}".format(
                    route,
                    output["name"].split()[0]
                )
            }

        # Search response again for the actual object
        resourceOutput = searchResponse(resourceRequest.json()["results"], filteredInput)

        if resourceOutput == "UNKNOWN": return "UNKNOWN"

        return {"route": route, "matchedObj": resourceOutput}

    # If already got the resource object, just return it
    else: return output

###
# FUNC NAME: constructResponse
# FUNC DESC: Constructs embed responses from the API object.
# FUNC TYPE: Function
###
def constructResponse(args, route, matchedObj):
    responseEmbeds = []

    # Document
    if route == "documents/":
        documentEmbed = None

        # Description charecter length for embeds is 2048, titles is 256
        if len(matchedObj["desc"]) >= 2048:
            documentEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (DOCUMENT)".format(matchedObj["title"]), 
                description=matchedObj["desc"][:2047]
            )
            documentEmbed.add_field(name="Description Continued...", value=matchedObj["desc"][2048:])
        else:
            documentEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=matchedObj["title"], 
                description=matchedObj["desc"]
            )
        documentEmbed.add_field(name="Authors", value=matchedObj["author"], inline=False)
        documentEmbed.add_field(name="Link", value=matchedObj["url"], inline=True)
        documentEmbed.add_field(name="Version Number", value=matchedObj["version"], inline=True)
        documentEmbed.add_field(name="Copyright", value=matchedObj["copyright"], inline=False)

        documentEmbed.set_thumbnail(url="https://i.imgur.com/lnkhxCe.jpg")

        responseEmbeds.append(documentEmbed)

    # Spell
    elif route == "spells/":
        spellEmbed = None

        if len(matchedObj["desc"]) >= 2048:
            spellEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (SPELL)".format(matchedObj["name"]), 
                description=matchedObj["desc"][:2047]
            )
            spellEmbed.add_field(name="Description Continued...", value=matchedObj["desc"][2048:], inline=False)
        else:
            spellEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=matchedObj["name"], 
                description=matchedObj["desc"]
            )
        if matchedObj["higher_level"] != "": 
            spellEmbed.add_field(name="Higher Level", value=matchedObj["higher_level"], inline=False)
        
        spellEmbed.add_field(name="School", value=matchedObj["school"], inline=False)
        spellEmbed.add_field(name="Level", value=matchedObj["level"], inline=True)
        spellEmbed.add_field(name="Duration", value=matchedObj["duration"], inline=True)
        spellEmbed.add_field(name="Casting Time", value=matchedObj["casting_time"], inline=True)
        spellEmbed.add_field(name="Range", value=matchedObj["range"], inline=True)
        spellEmbed.add_field(name="Concentration?", value=matchedObj["concentration"], inline=True)
        spellEmbed.add_field(name="Ritual?", value=matchedObj["ritual"], inline=True)

        spellEmbed.add_field(name="Spell Components", value=matchedObj["components"], inline=True)
        if "M" in matchedObj["components"]: spellEmbed.add_field(name="Material", value=matchedObj["material"], inline=True)
        spellEmbed.add_field(name="Page Number", value=matchedObj["page"], inline=True)

        spellEmbed.set_thumbnail(url="https://i.imgur.com/W15EmNT.jpg")

        responseEmbeds.append(spellEmbed)

    # Monster
    elif route == "monsters/":
        ## 1ST EMBED ##
        monsterEmbedBasics = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (MONSTER): BASIC STATS".format(matchedObj["name"]), 
            description="**TYPE**: {}\n**SUBTYPE**: {}\n**ALIGNMENT**: {}\n**SIZE**: {}\n**CHALLENGE RATING**: {}".format(
                matchedObj["type"] if matchedObj["type"] != "" else "None", 
                matchedObj["subtype"] if matchedObj["subtype"] != "" else "None", 
                matchedObj["alignment"] if matchedObj["alignment"] != "" else "None",
                matchedObj["size"],
                matchedObj["challenge_rating"]
            )
        )

        # Str
        if matchedObj["strength_save"] != None:
            monsterEmbedBasics.add_field(
                name="STRENGTH",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["strength"],
                    matchedObj["strength_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="STRENGTH",
                value="**{}**".format(matchedObj["strength"]),
                inline=True
            )

        # Dex
        if matchedObj["dexterity_save"] != None:
            monsterEmbedBasics.add_field(
                name="DEXTERITY",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["dexterity"],
                    matchedObj["dexterity_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="DEXTERITY",
                value="**{}**".format(matchedObj["dexterity"]),
                inline=True
            )

        # Con
        if matchedObj["constitution_save"] != None:
            monsterEmbedBasics.add_field(
                name="CONSTITUTION",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["constitution"],
                    matchedObj["constitution_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="CONSTITUTION",
                value="**{}**".format(matchedObj["constitution"]),
                inline=True
            )

        # Int
        if matchedObj["intelligence_save"] != None:
            monsterEmbedBasics.add_field(
                name="INTELLIGENCE",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["intelligence"],
                    matchedObj["intelligence_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="INTELLIGENCE",
                value="**{}**".format(matchedObj["intelligence"]),
                inline=True
            )

        # Wis
        if matchedObj["wisdom_save"] != None:
            monsterEmbedBasics.add_field(
                name="WISDOM",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["wisdom"],
                    matchedObj["wisdom_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="WISDOM",
                value="**{}**".format(matchedObj["wisdom"]),
                inline=True
            )

        # Cha
        if matchedObj["charisma_save"] != None:
            monsterEmbedBasics.add_field(
                name="CHARISMA",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["charisma"],
                    matchedObj["charisma_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="CHARISMA",
                value="**{}**".format(matchedObj["charisma"]),
                inline=True
            )

        # Hit points/dice
        monsterEmbedBasics.add_field(
            name="HIT POINTS ({})".format(str(matchedObj["hit_points"])), 
            value=matchedObj["hit_dice"], 
            inline=True
        )

        # Speeds
        monsterSpeeds = ""
        for speed in matchedObj["speed"].items(): 
            monsterSpeeds += "**{}**: {}\n".format(speed[0].upper(), str(speed[1]))
        monsterEmbedBasics.add_field(name="SPEED", value=monsterSpeeds, inline=True)

        # Armour
        monsterEmbedBasics.add_field(
            name="ARMOUR CLASS", 
            value="{} ({})".format(str(matchedObj["armor_class"]), matchedObj["armor_desc"]),
            inline=True
        )

        responseEmbeds.append(monsterEmbedBasics)

        ## 2ND EMBED ##
        monsterEmbedSkills = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (MONSTER): SKILLS & PROFICIENCIES".format(matchedObj["name"])
        )

        # Skills & Perception
        if matchedObj["skills"] != {} and matchedObj["perception"] != None:
            monsterSkills = ""
            for skill in matchedObj["skills"].items(): 
                monsterSkills += "**{}**: {}\n".format(skill[0].upper(), str(skill[1]))
            monsterEmbedSkills.add_field(name="SKILLS", value=monsterSkills, inline=True)

        elif matchedObj["perception"] != None:
            monsterEmbedSkills.add_field(name="PERCEPTION", value=str(matchedObj["perception"]), inline=True)
        else: pass

        # Senses
        monsterEmbedSkills.add_field(name="SENSES", value=matchedObj["senses"], inline=True)

        # Languages
        monsterEmbedSkills.add_field(name="LANGUAGES", value=matchedObj["languages"], inline=True)

        # Damage conditionals
        monsterEmbedSkills.add_field(
            name="STRENGTHS & WEAKNESSES",
            value="**VULNERABLE TO:** {}\n**RESISTANT TO:** {}\n**IMMUNE TO:** {}".format(
                matchedObj["damage_vulnerabilities"] if matchedObj["damage_vulnerabilities"] != None else "Nothing",
                matchedObj["damage_resistances"] if matchedObj["damage_resistances"] != None else "Nothing",
                matchedObj["damage_immunities"] if matchedObj["damage_immunities"] != None else "Nothing" 
                    + ", "
                        + matchedObj["condition_immunities"] if matchedObj["condition_immunities"] != None else "Nothing",
            ),
            inline=False
        )

        responseEmbeds.append(monsterEmbedSkills)

        ## 3RD EMBED ##
        monsterEmbedActions = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (MONSTER): ACTIONS AND ABILITIES".format(matchedObj["name"])
        )

        # Actions
        for action in matchedObj["actions"]:
            monsterEmbedActions.add_field(
                name=action["name"],
                value=action["desc"],
                inline=False
            )
        
        # Reactions
        if matchedObj["reactions"] != "":
            for reaction in matchedObj["reactions"]:
                monsterEmbedActions.add_field(
                    name=reaction["name"],
                    value=reaction["desc"],
                    inline=False
                )

        # Specials
        for special in matchedObj["special_abilities"]:
            monsterEmbedActions.add_field(
                name=special["name"],
                value=special["desc"],
                inline=False
            )

        # Spells
        if matchedObj["spell_list"] != []:
            for spell in matchedObj["spell_list"]:
                spellSplit = spell.replace("-", " ").split("/")

                # Remove trailing /, leaving the spell name as the last element in list
                del spellSplit[-1]

                monsterEmbedActions.add_field(
                    name=spellSplit[-1].upper(),
                    value="To see spell info, `?searchdir SPELLS {}`".format(spellSplit[-1].upper()),
                    inline=False
                )

        responseEmbeds.append(monsterEmbedActions)

        ## 4TH EMBED (only used if it has legendary actions) ##
        if matchedObj["legendary_desc"] != "":
            monsterEmbedLegend = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (MONSTER): LEGENDARY ACTIONS AND ABILITIES".format(matchedObj["name"]),
                description=matchedObj["legendary_desc"]
            )

            for action in matchedObj["legendary_actions"]:
                monsterEmbedLegend.add_field(
                    name=action["name"],
                    value=action["desc"],
                    inline=False
                )

            responseEmbeds.append(monsterEmbedLegend)

        # Author & Image for all embeds
        for embed in responseEmbeds:
            if matchedObj["img_main"] != None: embed.set_thumbnail(url=matchedObj["img_main"])
            else: embed.set_thumbnail(url="https://i.imgur.com/6HsoQ7H.jpg")

    # Background
    elif route == "background/":
        backgroundEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (BACKGROUND)".format(matchedObj["name"])
        )

        # Description
        backgroundEmbed.add_field(name="DESCRIPTION", value=matchedObj["desc"], inline=False)

        # Profs
        if matchedObj["tool_proficiencies"] != None: 
            backgroundEmbed.add_field(name="PROFICIENCIES", value="**SKILL**: {}\n**TOOL**: {}".format(
                matchedObj["skill_proficiencies"],
                matchedObj["tool_proficiencies"]
                ),
                inline=True
            )
        else:
            backgroundEmbed.add_field(name="PROFICIENCIES", value="**SKILL**: {}".format(
                matchedObj["skill_proficiencies"]
                ),
                inline=True
            )

        # Languages
        if matchedObj["languages"] != None: backgroundEmbed.add_field(name="LANGUAGES", value=matchedObj["languages"], inline=True)

        # Equipment
        backgroundEmbed.add_field(name="EQUIPMENT", value=matchedObj["equipment"], inline=False)

        # Feature
        backgroundEmbed.add_field(name=matchedObj["feature"], value=matchedObj["feature_desc"], inline=False)

        # Charecteristics
        if matchedObj["suggested_characteristics"] != None:
            backgroundEmbed.add_field(name="CHARECTERISTICS", value=matchedObj["suggested_characteristics"], inline=False)

        backgroundEmbed.set_thumbnail(url="https://i.imgur.com/GhGODan.jpg")

        responseEmbeds.append(backgroundEmbed)

    # Plane
    elif route == "planes/":
        planeEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (PLANE)".format(matchedObj["name"]),
            description=matchedObj["desc"]
        )

        
        planeEmbed.set_thumbnail(url="https://i.imgur.com/GJk1HFh.jpg")

        responseEmbeds.append(planeEmbed)

    # Section (NOT SUPPORTED YET)
    elif route == "sections/":
        sectionEmbedDesc = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (SECTION): BASICS".format(matchedObj["name"]),
            description="**TYPE**\n{}".format(matchedObj["parent"])
        )

        # Desc is organised into titles and descriptions, seperated by hashses. There is also a general description at start
        splitDesc = matchedObj["desc"].split("\n")

        # Remove empty strings from array. Can't use filter since we need to work with index() later on.
        for entry in splitDesc: 
            if entry == "": splitDesc.remove(entry)

        # Find the general description
        firstTitleIndex = 0
        generalDescription = ""

        for line in splitDesc:

            # If we hit a title, stop and record where. Otherwise, add to our general description
            if line[0] == "#":
                firstTitleIndex = splitDesc.index(line)
                break
            else: generalDescription += " " + line

        sectionEmbedDesc.add_field(name="DESCRIPTON", value=generalDescription, inline=False)
        responseEmbeds.append(sectionEmbedDesc)

        # Remove general description from the list to help parse the rest of it
        lineCount = 0
        while lineCount < firstTitleIndex:
            del splitDesc[0]
            lineCount += 1

        # Append our titles and associated descriptions to a dictionary
        sectionDict = {}

        currentTitle = ""
        for entry in splitDesc:

            # We've hit a title!
            if entry[0] == "#":

                # Add to the dictionary
                currentTitle = entry
                sectionDict[currentTitle] = ""

            # Continue adding to description
            else:
                sectionDict[currentTitle] += "\n" + entry


        # Finally, we convert our dictionary to embeds
        for title, desc in sectionDict.items():

            # Create a new embed so we have the most charecters possible to work with
            if len(desc) >= 2048:
                sectionEmbedBlock = discord.Embed(
                    colour=discord.Colour.green(),
                    title="{} (SECTION): {}".format(matchedObj["name"], title),
                    description=desc[:2047]
                )
                sectionEmbedBlock.add_field(name="Description Continued", value=desc[2048:], inline=False)

            else:
                sectionEmbedBlock = discord.Embed(
                    colour=discord.Colour.green(),
                    title="{} (SECTION): {}".format(matchedObj["name"], title),
                    description=desc
                )

            responseEmbeds.append(sectionEmbedBlock)

        # Finish up
        for embed in responseEmbeds: embed.set_thumbnail(url="https://i.imgur.com/J75S6bF.jpg")

    # Feat
    elif route == "feats/":
        featEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (FEAT)".format(matchedObj["name"]),
            description="PREREQUISITES: {}".format(matchedObj["prerequisite"])
        )
        featEmbed.add_field(name="DESCRIPTION", value=matchedObj["desc"], inline=False)
        featEmbed.set_thumbnail(url="https://i.imgur.com/X1l7Aif.jpg")

        responseEmbeds.append(featEmbed)

    # Condition
    elif route == "conditions/":

        if len(matchedObj["desc"]) > 2048:
            conditionEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (CONDITION)".format(matchedObj["name"]),
                description=matchedObj["desc"][:2047]
            )
            conditionEmbed.add_field(name="DESCRIPTION continued...", value=matchedObj["desc"][2048:], inline=False)

        else:
            conditionEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (CONDITION)".format(matchedObj["name"]),
                description=matchedObj["desc"]
            )
        conditionEmbed.set_thumbnail(url="https://i.imgur.com/tOdL5n3.jpg")

        responseEmbeds.append(conditionEmbed)

    # Race
    elif route == "races/":

        raceEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (RACE)".format(matchedObj["name"]),
            description=matchedObj["desc"]
        )

        # Asi Description
        raceEmbed.add_field(name="BENEFITS", value=matchedObj["asi_desc"], inline=False)

        # Age, Alignment, Size
        raceEmbed.add_field(name="AGE", value=matchedObj["age"], inline=True)
        raceEmbed.add_field(name="ALIGNMENT", value=matchedObj["alignment"], inline=True)
        raceEmbed.add_field(name="SIZE", value=matchedObj["size"], inline=True)
        
        # Speed
        for speedType, speed in matchedObj["speed"].items():
            raceEmbed.add_field(name="SPEED ({})".format(speed), value=speedType, inline=False)

        # Speed Description
        raceEmbed.add_field(name="SPEED DESCRIPTION", value=matchedObj["speed_desc"], inline=False)

        # Languages
        raceEmbed.add_field(name="LANGUAGES", value=matchedObj["languages"], inline=True)

        # Vision buffs
        if matchedObj["vision"] != "":
            raceEmbed.add_field(name="VISION", value=matchedObj["vision"], inline=True)

        # Traits
        if matchedObj["traits"] != "":

            if len(matchedObj["traits"]) > 1024:
                raceEmbed.add_field(name="TRAITS", value=matchedObj["traits"][:1023], inline=False)
                raceEmbed.add_field(name="TRAITS continued...", value=matchedObj["traits"][1024:], inline=False)
            else:
                raceEmbed.add_field(name="TRAITS", value=matchedObj["traits"], inline=False)

        raceEmbed.set_thumbnail(url="https://i.imgur.com/OUSzh8W.jpg")
        responseEmbeds.append(raceEmbed)

        # Start new embed for any subraces
        if matchedObj["subraces"] != []:

            for subrace in matchedObj["subraces"]:

                subraceEmbed = discord.Embed(
                    colour=discord.Colour.green(),
                    title="{} (SUBRACE OF {})".format(subrace["name"], matchedObj["name"]),
                    description=subrace["desc"]
                )

                # Subrace asi's
                subraceEmbed.add_field(name="SUBRACE BENEFITS", value=subrace["asi_desc"], inline=False)

                # Subrace traits
                if subrace["traits"] != "":

                    if len(subrace["traits"]) > 1024:
                        subraceEmbed.add_field(name="TRAITS", value=subrace["traits"][:1023], inline=False)
                        subraceEmbed.add_field(name="TRAITS continued...", value=subrace["traits"][1024:], inline=False)
                    else:
                        subraceEmbed.add_field(name="TRAITS", value=subrace["traits"], inline=False)

                subraceEmbed.set_thumbnail(url="https://i.imgur.com/OUSzh8W.jpg")
                responseEmbeds.append(subraceEmbed)
    
    # Class
    elif route == "classes/":

        # 1st Embed (BASIC)
        if len(matchedObj["desc"] > 2047):
            classDescEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (CLASS): Basics".format(matchedObj["name"]),
                description=matchedObj["desc"][:2047]
            )

            classDescEmbed.add_field(name="DESCRIPTION Continued", value=matchedObj["desc"][2048:], inline=False)

        else:
            classDescEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (CLASS)".format(matchedObj["name"]),
                description=matchedObj["desc"][:2047]
            )

        responseEmbeds.append(classDescEmbed)

        # 2nd Embed (TABLE)
        if len(matchedObj["table"]) > 2047:
            classTableEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (CLASS): Table".format(matchedObj["name"]),
                description=matchedObj["desc"][:2047]
            )
            classTableEmbed.add_field(name="TABLE CONTINUED", value=matchedObj["desc"][2048:], inline=False)
        
        else:
            classTableEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (CLASS): Table".format(matchedObj["name"]),
                description=matchedObj["desc"]
            )

        responseEmbeds.append(classTableEmbed)


        # 3rd Embed (DETAILS)
        classDetailsEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (CLASS): Details".format(matchedObj["name"]),
            description="ARMOUR: {}\nWEAPONS: {}\nTOOLS: {}\nSAVE THROWS: {}\nSKILLS: {}".format(
                matchedObj["prof_armor"],
                matchedObj["prof_weapons"],
                matchedObj["prof_tools"],
                matchedObj["prof_saving_throws"],
                matchedObj["prof_skills"]
            )
        )

        # Profs
        classDetailsEmbed.add_field(
            name="Hit points",
            value="Hit Dice: {} | HP at first level: {} | HP at other levels: {}".format(
                matchedObj["hit_dice"],
                matchedObj["hp_at_1st_level"],
                matchedObj["hp_at_higher_levels"]
            ),
            inline=False
        )

        # Equipment
        if len(matchedObj["equipment"]) > 1023:
            classDetailsEmbed.add_field(name="EQUIPMENT", value=matchedObj["equipment"][:1023], inline=False)
            classDetailsEmbed.add_field(name="EQUIPMENT continued", value=matchedObj["equipment"][1024:], inline=False)
        else:
            classDetailsEmbed.add_field(name="EQUIPMENT", value=matchedObj["equipment"], inline=False)
        
        # Spell casting
        if matchedObj["spellcasting_ability"] != "":
            classDetailsEmbed.add_field(name="CASTING ABILITY", value=matchedObj["spellcasting_ability"], inline=False)
        
        # Subtypes
        if matchedObj["subtypes_name"] != "":
            classDetailsEmbed.add_field(name="SUBTYPES", value=matchedObj["subtypes_name"], inline=False)

        # 4th Embed (ARCHETYPES)
        if matchedObj["archetypes"] != []:

            for archtype in matchedObj["archetypes"]:

                archTypeEmbed = None

                if len(archtype["desc"]) > 2047:

                    archTypeEmbed = discord.Embed(
                        colour=discord.Colour.green(),
                        title="{} (ARCHETYPES)".format(archtype["name"]),
                        description=archtype["desc"][:2047]
                    )
                    archTypeEmbed.add_field(name="Description Continued", value=archtype["desc"][2048:], inline=False)

                else:
                    archTypeEmbed = discord.Embed(
                        colour=discord.Colour.green(),
                        title="{} (ARCHETYPES)".format(archtype["name"]),
                        description=archtype["desc"]
                    )

                responseEmbeds.append(archTypeEmbed)

        # Finish up
        for embed in responseEmbeds: embed.set_thumbnail(url="https://i.imgur.com/Mjh6AAi.jpg")
   
    # Magic Item
    elif route == "magicitems/":
        magicItemEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (MAGIC ITEM)".format(matchedObj["name"]),
            description=matchedObj["desc"]
        )

        magicItemEmbed.add_field(name="TYPE", value=matchedObj["type"], inline=True)
        magicItemEmbed.add_field(name="RARITY", value=matchedObj["rarity"], inline=True)

        if matchedObj["requires_attunement"] == "requires_attunement":
            magicItemEmbed.add_field(name="ATTUNEMENT?", value="YES", inline=True)
        else:
            magicItemEmbed.add_field(name="ATTUNEMENT REQUIRED?", value="NO", inline=True)

        magicItemEmbed.set_thumbnail(url="https://i.imgur.com/2wzBEjB.png")

        responseEmbeds.append(magicItemEmbed)

    # Weapon
    elif route == "weapons/":
        weaponEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (WEAPON)".format(matchedObj["name"]),
            description="PROPERTIES: {}".format(
                " | ".join(matchedObj["properties"]) if matchedObj["properties"] != [] else "None"
            )
        )
        weaponEmbed.add_field(
            name="DAMAGE",
            value="{} ({})".format(
                matchedObj["damage_dice"], matchedObj["damage_type"]
            ),
            inline=True
        )

        weaponEmbed.add_field(name="CATEGORY", value=matchedObj["category"], inline=True)
        weaponEmbed.add_field(name="COST", value=matchedObj["cost"], inline=True)
        weaponEmbed.add_field(name="WEIGHT", value=matchedObj["weight"], inline=True)

        weaponEmbed.set_thumbnail(url="https://i.imgur.com/pXEe4L9.png")

        responseEmbeds.append(weaponEmbed)
    
    else:
        # Don't add a footer to an error embed
        global partialMatch
        partialMatch = False

        noRouteEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="The matched item's type (i.e. spell, monster, etc) was not recognised",
            description="Please create an issue describing this failure and with the following values at https://github.com/shadowedlucario/oghma/issues\n**Input**: {}\n**Route**: {}\n**Troublesome Object**: {}".format(
                args, route, matchedObj
            )
        )
        noRouteEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
        
        responseEmbeds.append(noRouteEmbed)

    return responseEmbeds


###
# FUNC NAME: codeError
# FUNC DESC: Sends an embed informing the user that there has been an API request failure
# FUNC TYPE: Error
###
def codeError(statusCode, query):
    codeEmbed = discord.Embed(
        colour=discord.Colour.red(),
        title="ERROR - API Request FAILED. Status Code: **{}**".format(str(statusCode)), 
        description="Query: {}".format(query)
    )
        
    codeEmbed.add_field(
        name="For more idea on what went wrong:",
        value="See status codes at https://www.django-rest-framework.org/api-guide/status-codes/",
        inline=False
    )

    codeEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
    codeEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

    return codeEmbed

###
# FUNC NAME: on_ready
# FUNC DESC: Tells you when bot is ready to accept commands. Also cleans up temp files.
# FUNC TYPE: Command
###
@bot.event
async def on_ready():
    print("Logged in as\n{}\n{}\n------".format(bot.user.name, bot.user.id))

    # Cleanup from last run
    print("Cleaning up old files...")

    # TODO: Need to make this public to all functions
    print("Trying to clean entities.txt")
    if os.path.exists("entities.txt"):
        os.remove("entities.txt")

        if os.path.exists("entities.txt"):
            print("ERROR: entities.txt could not be deleted")
        else:
            print("entities.txt successfully deleted!")
    else:
        print("entities.txt does not exist. Skipping...")
    print("------")

    # All done!
    print("READY!")

###
# FUNC NAME: ?ping
# FUNC DESC: Pings the bot to check it is live
# FUNC TYPE: Command
###
@bot.command(name='ping', help='Pings the bot.\nUsage: !ping')
async def ping(ctx):
    await ctx.send('Pong!')

###
# FUNC NAME: ?search [ENTITY]
# FUNC DESC: Queries the Open5e search API, basically searches the whole thing for the ENTITY.
# ENTITY: The DND entity you wish to get infomation on.
# FUNC TYPE: Command
###
@bot.command(
    pass_context=True,
    name='search',
    help='Queries the Open5e API to get the entities infomation.\nUsage: ?search [ENTITY]',
    usage='?search [ENTITY]'
)
async def search(ctx, *args):

    # Import & reset globals
    global partialMatch
    partialMatch = False

    # Verify we have args
    if len(args) <= 0:
        usageEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="No arguments were given. Command requires at least one argument", 
            description="USAGE: `?search [D&D OBJECT YOU WANT TO SEARCH FOR]`"
        )

        usageEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        usageEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=usageEmbed)

    # Verify arg length isn't over limits
    if len(args) > 200:
        argumentsEmbed = discord.Embed(
            color=discord.Colour.red(),
            title="Invalid argument length",
            description="This command does not support more than 200 words in a single message. Try splitting up your query."
        )
        argumentsEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
        argumentsEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=argumentsEmbed)

    # Send directory contents if no search term given
    if len(args) == 1:

        await ctx.send(embed=discord.Embed(
            color=discord.Colour.blue(),
            title="GETTING ALL SEARCHABLE ENTITIES IN SEARCH/ ENDPOINT...",
            description="WARNING: This may take a while!"
        ))

        # Get objects from directory, store in txt file
        directoryRequest = requests.get("https://api.open5e.com/search/?format=json&limit=10000")

        if directoryRequest.status_code != 200: 
            return await ctx.send(embed=codeError(
                directoryRequest.status_code,
                "https://api.open5e.com/search/?format=json&limit=10000"
                )
            )

        entityFile = open("entities.txt", "a+")
        for entity in directoryRequest.json()["results"]:
            if "title" in entity.keys():
                entityFile.write("{}\n".format(entity["title"]))
            else:
                entityFile.write("{}\n".format(entity["name"]))

        entityFile.close()

        # Send embed notifying start of the spam stream
        detailsEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="See `entities.txt` for all searchable entities in this endpoint", 
            description="Due to discord charecter limits regarding embeds, the results below have to be sent in a file. Yes I know this is far from ideal but it's the best I can do!"
        )

        detailsEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        detailsEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        await ctx.send(embed=detailsEmbed)

        # Send entites file
        return await ctx.send(file=discord.File("entities.txt"))

    # Filter input to remove whitespaces and set lowercase
    filteredInput = "".join(args).lower()

    # Search API
    await ctx.send(embed=discord.Embed(
        color=discord.Colour.blue(),
        title="SEARCHING ALL ENDPOINTS FOR {}...".format(args),
        description="WARNING: This may take a while!"
    ))
    
    # Use first word to narrow search results down for quicker response on some directories
    match = requestAPI("https://api.open5e.com/search/?format=json&limit=10000&text={}".format(str(args[0])), filteredInput, True)

    # An API Request failed
    if isinstance(match, dict) and "code" in match.keys():
        return await ctx.send(embed=codeError(match["code"], match["query"]))

    # Searching algorithm hit an invalid object
    elif match == "UNKNOWN":
        unknownMatchEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="ERROR", 
            description="I found an entity in the API database that doesn't contain a `name` or `docuement` attribute. Please report this to https://github.com/shadowedlucario/oghma/issues"
        )

        unknownMatchEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
        unknownMatchEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=unknownMatchEmbed)

    # No entity was found
    elif match == None:
        noMatchEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="ERROR", 
            description="No matches found for **{}** in the search endpoint".format(filteredInput)
        )

        noMatchEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        noMatchEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=noMatchEmbed)

    # Otherwise, construct & send response embeds
    else:
        responseEmbeds = constructResponse(args, match["route"], match["matchedObj"])
        for embed in responseEmbeds:

            embed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

            # Note partial match in footer of embed
            if partialMatch == True: 
                embed.set_footer(text="NOTE: Your search term ({}) was a PARTIAL match to this entity.\nIf this isn't the entity you were expecting, try refining your search term or use ?searchdir instead".format(args))
            else:
                embed.set_footer(text="NOTE: If this isn't the entity you were expecting, try refining your search term or use ?searchdir instead")

            print("SENDING EMBED...")
            await ctx.send(embed=embed)

    print("DONE!")

###
# FUNC NAME: ?searchdir [RESOURCE] [ENTITY]
# FUNC DESC: Queries the Open5e RESOURCE API.
# RESOURCE:  Resource name (i.e. spells, monsters, etc.).
# ENTITY: The DND entity you wish to get infomation on.
# FUNC TYPE: Command
###
@bot.command(
    pass_context=True,
    name='searchdir',
    help='Queries the Open5e API to get the entities infomation from the specified resource.\nUsage: ?searchdir [RESOURCE] [ENTITY]',
    usage='?search [RESOURCE] [ENTITY]'
)
async def searchdir(ctx, *args):

    # Import & reset globals
    global partialMatch
    partialMatch = False

    # Verify we have arguments
    if len(args) <= 0:
        usageEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="No arguments were given. Command requires at least one argument", 
            description="USAGE: `?searchdir [DIRECTORY] [D&D OBJECT YOU WANT TO SEARCH FOR]`"
        )

        usageEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        usageEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=usageEmbed)

    # Filter the dictionary input
    # TODO: This is bugged. Seems to save the variable between commands.
    filteredDictionary = args[0].lower() + "/"

    # Filter input to remove whitespaces and set lowercase
    filteredInput = "".join(args[1:]).lower()

    # Get API Root
    rootRequest = requests.get("https://api.open5e.com?format=json")

    # Throw if Root request wasn't successfull
    if rootRequest.status_code != 200: 
        return await ctx.send(embed=codeError(rootRequest.status_code, "https://api.open5e.com?format=json"))

    # Verify arg length isn't over limits
    if len(args) > 200:
        argumentsEmbed = discord.Embed(
            color=discord.Colour.red(),
            title="Invalid argument length",
            description="This command does not support more than 200 words in a single message. Try splitting up your query."
        )
        argumentsEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
        argumentsEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=argumentsEmbed)

    # Send directory contents if no search term given
    if len(args) == 1:

        await ctx.send(embed=discord.Embed(
            color=discord.Colour.blue(),
            title="GETTING ALL SEARCHABLE ENTITIES IN {} ENDPOINT...".format(filteredDictionary.upper()),
            description="WARNING: This may take a while!"
        ))

        # Get objects from directory, store in txt file
        directoryRequest = requests.get("https://api.open5e.com/{}?format=json&limit=10000".format(filteredDictionary))

        if directoryRequest.status_code != 200: 
            return await ctx.send(embed=codeError(
                directoryRequest.status_code,
                "https://api.open5e.com/{}?format=json&limit=10000".format(filteredDictionary)
                )
            )

        entityFile = open("entities.txt", "a+")
        for entity in directoryRequest.json()["results"]:
            if "title" in entity.keys():
                entityFile.write("{}\n".format(entity["title"]))
            else:
                entityFile.write("{}\n".format(entity["name"]))

        entityFile.close()

        # Send embed notifying start of the spam stream
        detailsEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="See `entities.txt` for all searchable entities in this endpoint", 
            description="Due to discord charecter limits regarding embeds, the results below have to be sent in a file. Yes I know this is far from ideal but it's the best I can do!"
        )

        detailsEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        detailsEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")
        if "search" in filteredDictionary:
            detailsEmbed.set_footer(text="NOTE: The `search` endpoint is not searchable with `?searchdir`. Use `?search` instead for this.")

        await ctx.send(embed=detailsEmbed)

        # Send entites file
        return await ctx.send(file=discord.File("entities.txt"))

    # search/ endpoint is best used with the dedicated ?search command
    if "search" in filteredDictionary:
        
        # Remove search endpoint from list
        directories = list(rootRequest.json().keys())
        directories.remove("search")

        searchEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="Requested Directory (`{}`) is not a valid directory name".format(str(args[0])), 
            description="**Available Directories**\n{}".format(", ".join(directories))
        )

        searchEmbed.add_field(name="NOTE", value="Use `?search` for searching the `search/` directory. This has been done to cut down on parsing errors.")
        searchEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        searchEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=searchEmbed)

    # Verify resource exists
    if args[0] not in rootRequest.json().keys():

        # Remove search endpoint from list
        directories = list(rootRequest.json().keys())
        directories.remove("search")

        noResourceEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="Requested Directory (`{}`) is not a valid directory name".format(str(args[0])), 
            description="**Available Directories**\n{}".format(", ".join(directories))
        )

        noResourceEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        noResourceEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=noResourceEmbed)

    # Search API
    await ctx.send(embed=discord.Embed(
        color=discord.Colour.blue(),
        title="SEARCHING {} ENDPOINT FOR {}...".format(filteredDictionary.upper(), args),
        description="WARNING: This may take a while!"
    ))
    
    # Use first word to narrow search results down for quicker response on some directories
    match = requestAPI(
        "https://api.open5e.com/{}?format=json&limit=10000&text={}".format(
            filteredDictionary,
            str(args[1])
        ),
        filteredInput,
        False
    )

    # An API Request failed
    if isinstance(match, dict) and "code" in match.keys():
        return await ctx.send(embed=codeError(match.code, match.query))

    # Searching algorithm hit an invalid object
    elif match == "UNKNOWN":
        unknownMatchEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="ERROR", 
            description="I found an entity in the API database that doesn't contain a `name` or `docuement` attribute. Please report this to https://github.com/shadowedlucario/oghma/issues"
        )

        unknownMatchEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
        unknownMatchEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=unknownMatchEmbed)

    # No entity was found
    elif match == None:
        noMatchEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="ERROR", 
            description="No matches found for **{}** in the {} endpoint".format(filteredInput.upper(), filteredDictionary)
        )

        noMatchEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        noMatchEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=noMatchEmbed)

    # Otherwise, construct & send response embeds
    else:
        responseEmbeds = constructResponse(args, filteredDictionary, match)
        for embed in responseEmbeds:

            embed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

            # Note partial match in footer of embed
            if partialMatch == True: 
                embed.set_footer(text="NOTE: Your search term ({}) was a PARTIAL match to this entity.\nIf this isn't the entity you were expecting, try refining your search term or use ?searchdir instead".format(args))

            print("SENDING EMBED...")
            await ctx.send(embed=embed)

    print("DONE!")

bot.run(TOKEN)
