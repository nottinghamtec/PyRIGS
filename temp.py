from telegram_interface import models

# man = models.TelegramManager(token="135462350:AAEhnE-Nd90fQIYM988H3rfUKVsT2MI24_A")
# man.save()

man = models.TelegramManager.objects.all()[0]


man.lookupUpdates()

man.broadcastMessage("THIS IS A BROADCAST, CAN YOU HEAR ME?")

exit()