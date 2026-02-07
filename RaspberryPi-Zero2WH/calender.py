#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd4in2b_V2
import time
from PIL import Image,ImageDraw,ImageFont,ImageOps
import traceback

from datetime import date, datetime, timedelta
import ephem
import json

logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("CalEnder")

    logging.info("Defining pixel positions")

    pxDecoHeaderSeparatorY = 22
    pxDecoWeeknumberSeparatorX = 38

    pxWeekPadLeft = 8
    pxCalPadTop = 22
    pxWeekendSeparation = 7
    pxWeekSeparation = 25
    pxMonthSeparation = 7
    pxMondayX = 47
    pxDayInterval = 35
    pxDateCursorY = pxCalPadTop
    pxDateCursorX = pxMondayX

    logging.info("Calculating base dates")
    
    fourWeeks = timedelta(days=28)
    oneDay = timedelta(days=1)

    today = date.today()
    
    # For debugging (moving to a different date)
    #today = today + timedelta(days=1)
    
    fourWeeksAgo = today - fourWeeks
    firstMonth = fourWeeksAgo.month
    cursorDate = fourWeeksAgo - timedelta(days=fourWeeksAgo.weekday())
    cursorMonth = cursorDate.month
    
    ephemToday = ephem.Date(today.strftime("%Y/%m/%d"))
    nextNewMoon = ephem.next_new_moon(ephemToday)
    nextFullMoon = ephem.next_full_moon(ephemToday)
    
    if nextNewMoon > nextFullMoon:
        daysLeft = round(nextFullMoon - ephemToday)
        headerText = "Vollmond"
    else:
        daysLeft = round(nextNewMoon - ephemToday)
        headerText = "Neumond"
    
    if daysLeft == 0:
        headerText += " heute"
    elif daysLeft >= 16:
        if nextNewMoon > nextFullMoon:
            headerText = "Neumond heute"
        else:
            headerText = "Vollmond heute"
    elif daysLeft == 1:
        headerText = headerText + " morgen"
    elif daysLeft > 1:
        headerText = str(round(daysLeft)) + " Tage bis " + headerText

    homeLat = '50.0'
    homeLon = '10.0'

    home = ephem.Observer()
    home.lat, home.lon = homeLat, homeLon
    home.date = datetime.utcnow()

    moon = ephem.Moon()
    moon.compute(home)
    format = "%-H:%M"
    nextRising = home.next_rising(moon)
    nextSetting = home.next_setting(moon)
    moonrise = ephem.localtime(nextRising).strftime(format)
    moonset  = ephem.localtime(nextSetting).strftime(format)

    headerText += " ▲" + moonrise + " ▼" + moonset

    logging.info("Header text: " + headerText)


    logging.info("Displaying calendar")
    
    epd = epd4in2b_V2.EPD()
    logging.info("Init and clear")
    epd.init()
    epd.Clear()
    time.sleep(1)
    
    # Drawing on the image
    logging.info("Drawing")    
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)
    
    blackImage = Image.new('1', (epd.height, epd.width), 255)  # 126*298
    redImage = Image.new('1', (epd.height, epd.width), 255)  # 126*298
    drawBlack = ImageDraw.Draw(blackImage)
    drawRed = ImageDraw.Draw(redImage)
    
    
    with open('entries.json') as f:
        entries = json.load(f)
    
        for shownWeek in range(14):
            weekNumber = cursorDate.isocalendar().week
            pxWeekPositionX = pxWeekPadLeft if weekNumber > 9 else pxWeekPadLeft + 13
            drawBlack.text((pxWeekPositionX, pxDateCursorY), str(weekNumber), font = font24, fill = 0)

            for shownWeekday in range(7):
                dateNumber = cursorDate.strftime("%d")

                # Add some horizontal separation between the week and the weekend
                if cursorDate.weekday() == 5:
                    pxDateCursorX += pxWeekendSeparation
                    
                # Add a bit of vertical separation when the month changes (even during the week)
                if cursorMonth != cursorDate.month:
                    pxDateCursorY += pxMonthSeparation
                    cursorMonth = cursorDate.month

                left = pxDateCursorX - 3
                right = pxDateCursorX + 28
                top = pxDateCursorY + 1
                bottom = pxDateCursorY + 27
                    
                # Mark date if necessary
                isMarking2 = False
                year = cursorDate.strftime("%Y")
                month = cursorDate.strftime("%-m")
                day = cursorDate.strftime("%-d")
                if year in entries and month in entries[year] and day in entries[year][month]:
                    markings = entries[year][month][day]
                    if markings == 1:
                        drawRed.line((left-1, bottom-2, right+2, bottom-2), fill = 0)
                        drawRed.line((left-1, bottom-1, right+2, bottom-1), fill = 0)
                    elif markings == 2:
                        isMarking2 = True

                # Write the date
                if cursorDate == today:
                    drawRed.rectangle((left, top, right, bottom), fill = 0)                             # Paint a red rectangle
                    drawRed.text((pxDateCursorX, pxDateCursorY), dateNumber, font = font24, fill = 255) # Remove the red color where we want the date to show
                else:
                    if cursorDate.weekday() == 6:
                        drawRed.text((pxDateCursorX, pxDateCursorY), dateNumber, font = font24, fill = 0)
                    else:
                        if isMarking2:
                            drawRed.text((pxDateCursorX, pxDateCursorY), dateNumber, font = font24, fill = 0)
                        else:
                            drawBlack.text((pxDateCursorX, pxDateCursorY), dateNumber, font = font24, fill = 0)
                
                pxDateCursorX += pxDayInterval
                cursorDate += oneDay

            pxDateCursorY += pxWeekSeparation
            pxDateCursorX = pxMondayX

        drawBlack.text((5, 0), headerText, font = font18, fill = 0)
        drawBlack.line((0, pxDecoHeaderSeparatorY, 299, pxDecoHeaderSeparatorY), fill = 0)
        drawBlack.line((pxDecoWeeknumberSeparatorX, 22, pxDecoWeeknumberSeparatorX, 399), fill = 0)
    
    epd.display(epd.getbuffer(blackImage), epd.getbuffer(redImage))
    time.sleep(2)
    
    logging.info("Goto Sleep...")
    epd.sleep()
        
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd4in2b_V2.epdconfig.module_exit(cleanup=True)
    exit()
