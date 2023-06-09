import argparse
import glob
import os
import re
import pyexiv2
import PIL
from PIL import Image
from PIL import ImageOps
from PIL import ImageFont
from PIL import ImageDraw


parser = argparse.ArgumentParser()
parser.add_argument("directory", type=str, help="The directory with the photos you wish to infomark. By default the output directory will be created here as well.")
parser.add_argument("-d", "--date", action="store_true", help="Includes the Date Taken (local time) in the Infomark")
parser.add_argument("-a", "--altitude", action="store_true", help="Includes the Depth/Altitude in the Infomark, if present (Defaults to Feet)")
parser.add_argument("-t", "--temp", action="store_true", help="Includes the Temperature in the Infomark, if present (Defaults to Fahrenheit)")
parser.add_argument("-l", "--location", action="store_true", help="Attempts to use the ReelName as the Location, if not available then attempts to use the ImageUniqueID in the Infomark")
parser.add_argument("-g", "--gps", action="store_true", help="Includes the GPS location of the photo, in the form ##°##\'###\" if present, in the Infomark")
parser.add_argument("-S", "--SILLY", action="store_true", help="Silly Standards, everyone knows Feet and F° are the superior measurements (except for in SCIENCE!). And because the author " + 
                    " is from `MERICA! those silly standards will be ignored by default unless this flag is set. That means that all numbers that should be in Metric will be interpreted as imperial")
parser.add_argument("-T", "--title", action="store_true", help="Includes the Title if present, (EXIF data refers to it as XPTitle, so may be a Windows only thing)")
parser.add_argument("-A", "--author", action="store_true", help="Includes the Author if present, elses uses the Copywrite in the Infomark")
parser.add_argument("-D", "--description", action="store_true", help="Includes the Description if present")
parser.add_argument("-J", "--subject", action="store_true", help="Includes the Subject if present, (EXIF data refers to it as XPSubject, so may be a Windows only thing)")
parser.add_argument("-C", "--comment", action="store_true", help="Includes the Comment if present, (EXIF data refers to it as XPComment, so may be a Windows only thing)")
parser.add_argument("-m", "--misc", type=str, help="Any additional text you wish included. \\n can be used to insert new lines")
parser.add_argument("-v", "--verbose", action="store_true", help="Flood the console with Print statements")
parser.add_argument("-c", "--colour", type=str, default="White", help="Colour to use for Infomark. Takes standard English colors as input (e.g. Blue) Defaults to White")
parser.add_argument("-o", "--opacity", type=int, default=75, help="Opacity to use for Infomark as an integer between 0 (transparent) and 255 (completely opaque). Defaults to 75")
parser.add_argument("-s", "--size", type=float, default=2, help="Size of the font to use, as a percentage of the overall picture height. Default is 2.0, maximum is 98")
parser.add_argument("-q", "--quality", type=int, default=90, help="The 'quality' of the JPEG compression as a percentage from 1-100, defaulting to 90. This is primarily controls the size of the resulting picture. " +
                    "WARNING: Qualities over 95 appear to get wonky, sometimes resulting in photos significantly larger than the original at 100%.")
parser.add_argument("-f", "--folder", type=str, default="InfoMarked\\", help="Directory that InfoMarked copies of pictures will be saved to. Defaults to a new one called InfoMarked at the location of the photos")
args = parser.parse_args()

#Determine the outputlocation for all Pictures modified during this iteration. Up here so we don't bother calculating it for every photo
outputLoc = ""
if os.path.isabs(args.folder):
    outputLoc = args.folder
else:
    outputLoc = args.directory + args.folder
if not os.path.exists(outputLoc):
    os.mkdir(outputLoc)
print(outputLoc)

def parseTude(tude, ref):
    '''Parses a single L***tude from the ugly EXIF standard to something prettier
       @tude - The EXIF formated Longitute or Latitude to be parsed
       @ref - The EXIF N/E/S/W reference to use as part of the coordinate  '''
    
    coordFrac = re.split("/[0-9]+\s", tude+" ")    
    coord = f"{coordFrac[0]}° {coordFrac[1]}' {round(int(coordFrac[2])/100)}\" {ref}"    
    return coord

def parseDepth(data):
    ''' Attempts to retrieve the depth or altitude from the EXIF metadata and then format it appropriately for the Infomark
        @data - EXIF metadata that may contain either WaterDepth or GPSAltitude information'''    
    try:
        depthFraction = (data['Exif.Photo.WaterDepth']).split("/")   
        depth = str((int(depthFraction[0])/int(depthFraction[1]))) 
    except KeyError:
        try:
            if args.verbose:
                print("No waterdepth found")

            #If Ref = 1, then we are dealing with negative altitudes
            if(int(data['Exif.GPSInfo.GPSAltitudeRef'])):
                depth = "-"
            else:
                depth = ""
            depthFraction = (data['Exif.GPSInfo.GPSAltitude']).split("/")            
            depth = depth + str((int(depthFraction[0])/int(depthFraction[1])))       
        except KeyError:
            if args.verbose:
                print("No GPSAltitude found")
            return
    if args.SILLY:
        depth = depth + "m"
    else:
        depth = depth + "ft"
    return depth    

def infoMark(data, photo, originData):
    ''' Takes a photo and list of Strings and writes them in vertical order in the bottom left of the photo
        @data - The List of Strings to infomark the photo
        @photo - Location of the Picture to be marked 
        @originData - The original metadata that needs to be added back to the new photo'''
    if args.verbose:
        print(data)
        print(photo)

    if photo.upper().endswith("NEF"):
        return

    #Get the photo and make a copy to edit that is RGBA so we can have transparent watermarks, then transpose it to match prefered orientation
    origin = ImageOps.exif_transpose(Image.open(photo).convert("RGBA"))    
    
    #Get the width and height of the image 
    width, height = origin.size

    #Preparing the text watermark
    mark = Image.new("RGBA", origin.size, (255, 255, 255, 0))

    # Adding custom font
    fnt = ImageFont.truetype("arial.ttf", round(height/100*args.size))
    
    # Creating image text
    image = ImageDraw.Draw(mark)
    
    # Make the text written into center as one giant block so the text() will take it
    dataMark = ""
    for datum in data:
        dataMark = f"{dataMark}\n{datum}"
    if args.verbose:
        print(dataMark)
    #Calculate the starting height based on number of datum being used
    startingLoc = round((height/100 * 99) - (round(height/100*args.size) * len(data)))
    #startingLoc = round(height - (round(height/100*args.size) * len(data)))
    #I couldn't figure out how to make the text colour be smart about changing based on light or dark backgrounds, so now it's the user's problem
    color =(PIL.ImageColor.getrgb(args.colour) + (args.opacity,))    
    #image.text((round(width/100), startingLoc), dataMark, font=fnt, fill=(color))
    image.text((round(width/100), round(height/100*99)), dataMark, anchor="ld", font=fnt, fill=(color))
    
    # Combine the image with text watermark and convert back to RGB
    out = Image.alpha_composite(origin, mark).convert("RGB")

    # Save the image to destination directory
    fileLoc = outputLoc + photo.rsplit('\\', 1)[1]
    if args.verbose:
        print(fileLoc)
    #Pillow did some funky things at 100% quality, pictures ended up significantly larger than the originals. 90% Seemed fine and offered significant space savings
    out.save(fileLoc, quality=args.quality,exif=origin.info['exif'])

c = 0
#Iterates over everything in the given directory, filtering pictures and adding an Infomark based on the optional args provided
for pic in filter(os.path.isfile, glob.glob(args.directory + '*')):
    c = c + 1
    if c % 20 == 0:
        print(f"Processed {c} files.")
    try:
        #Fetch the image metadata so we can grab the date the camera thinks the photo was taken, to ensure we can process these in order taken
        exiv_image = pyexiv2.Image(pic)
        data = exiv_image.read_exif()

        info = []

        #Check if user wanted to include time, if so truncate to day and include
        if args.date:
            if data.get('Exif.Image.DateTimeOriginal'):
                info.append((data['Exif.Image.DateTimeOriginal']).split()[0].replace(":","/"))
            elif data.get('Exif.Photo.DateTimeOriginal'):
                info.append((data['Exif.Photo.DateTimeOriginal']).split()[0].replace(":","/"))
            elif data.get('Exif.Photo.DateTimeDigitized'):
                info.append((data['Exif.Photo.DateTimeDigitized']).split()[0].replace(":","/"))
            elif data.get('Exif.Image.DateTime'):
                info.append((data['Exif.Image.DateTime']).split()[0].replace(":","/"))
            elif args.verbose:
                print("No DateTime found for photo: " + pic)

        #If Title was requested, attempt to include
        if args.title:
            try:                
                info.append(data['Exif.Image.XPTitle'].removesuffix('\x00'))
            except KeyError:
                try:
                    if args.verbose:
                        print("No Title found for photo: " + pic)
                    info.append(data['Exif.Photo.ImageUniqueID'])                    
                except KeyError:
                    if args.verbose:
                        print("No UniqueID found for photo: " + pic)

        #If Subject was requested, attempt to include
        if args.subject:
            try:                
                info.append(data['Exif.Image.XPSubject'].removesuffix('\x00'))
            except KeyError:
                if args.verbose:
                    print("No Subject found for photo: " + pic)

        #If Comments were requested, attempt to include
        if args.comment:
            try:                
                info.append(data['Exif.Image.XPComment'].removesuffix('\x00'))
            except KeyError:
                if args.verbose:
                    print("No Comment found for photo: " + pic)

        #If Location was requested, attempt to include
        if args.location:
            try:                
                info.append(data['Exif.Image.ReelName'])
            except KeyError:
                if args.verbose:
                    print("No Location found for photo: " + pic)

        if args.gps:
            try:
                #Get the local timestamp the picture was taken
                lat = parseTude(data['Exif.GPSInfo.GPSLatitude'], data['Exif.GPSInfo.GPSLatitudeRef'])
                long = parseTude(data['Exif.GPSInfo.GPSLongitude'], data['Exif.GPSInfo.GPSLongitudeRef'])
                info.append(f"{lat} {long}")                
            except KeyError:
                if args.verbose:
                    print("No GPS Location Found for photo: " + pic)

        
        #Because Depth and Temperature seem likely to be together and are tiny, attempt to put them on the same line
        env = ""
        #If Depth/Altitude was requested, attempt to include
        if args.altitude:
            depth = parseDepth(data)
            if depth:
                env = f"{parseDepth(data)} "

        #Check if user wanted to include temperature, if so clean and include
        if args.temp:
            try:
                temp = (data['Exif.Photo.Temperature']).split("/",1)[0]
                if args.SILLY:
                    temp = temp + "°C"
                else:
                    temp = temp + "°F"
                env = env + temp
            except KeyError:
                if args.verbose:
                    print("No Temperature found for photo: " + pic)
                pass
        
        if env:
            info.append(env)

        #If the user specified addional text to add to the image do so now. No safety checks, what could possibly go wrong?
        if args.description:
            try:
                info.append(data['Exif.Image.ImageDescription'].removesuffix('\x00'))
            except KeyError:
                if args.verbose:
                    print("No Description found for photo: " + pic)

        #If the user specified addional text to add to the image do so now. No safety checks, what could possibly go wrong?
        if args.misc:
            for surprise in args.misc.split("\\n"):
                info.append(surprise) 

        #If Author was requested, attempt to include. If it cannot be found try Copyright next
        if args.author:
            try:                
                info.append(data['Exif.Image.XPAuthor'].removesuffix('\x00'))
            except KeyError:
                try:
                    if args.verbose:
                        print("No Author found for photo: " + pic)
                    #This key always returned an empty string on our test photos, don't know if that is always true
                    if data['Exif.Image.Copyright']:
                        info.append(data['Exif.Image.Copyright'])
                    elif args.verbose:
                        print("No Copyright found for photo: " + pic)
                except KeyError:
                    if args.verbose:
                        print("No Copyright found for photo: " + pic)
                    pass
        
        #Close the image because the library tells us to and we'll need to use a different library to do the actual photo manipulation
        exiv_image.close()        

        infoMark(info, pic, data)
    #If we can't open it, it must not be a picture so move on
    except RuntimeError:
        continue