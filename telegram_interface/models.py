from django.db import models

import telegram
import time

from django.conf import settings

class TelegramManager(models.Model):
	offset = models.CharField(max_length=255, null=False, blank=True, default="")
	token = models.CharField(max_length=255, null=False, blank=False)

	@property
	def bot(self):
		return telegram.Bot(token=self.token)

	def lookupUpdates(self):
		updates = self.bot.getUpdates(offset=self.offset)
		if len(updates) > 0:
			self.parseUpdates(updates)
			self.offset = updates[-1].to_dict()["update_id"]+1
			self.save()

	def parseUpdates(self,updates):
		for update in updates:	
			chat_id = update.message.chat_id

			try:
			   chat_object = Chat.objects.get(chat_id=chat_id,manager=self)
			   self.knownChat(update,chat_object)

			except Chat.DoesNotExist:
			   self.unknownChat(update)

	def unknownChat(self,update):
		text = update.message.text

		if text.startswith("/start"):
			chat = Chat(chat_id=update.message.chat.id,manager=self)
			chat.save()

			chat.sendMessage( "Hi, I'll send you updates on any rigs.")
		else:
			self.bot.sendMessage(chat_id=update.message.chat.id, text="I don't know you, and won't talk to you until you /start me.")

	def knownChat(self, update, chat):
		text = update.message.text

		if text.startswith("/stop"):
			chat.sendMessage( "Ok, I'll stop sending you messages. If you want to restart just type /start")
			chat.delete()
		elif text.startswith("/start"):
			chat.sendMessage("I already know you, no need to /start me again!")
		elif text.startswith("/"):
			chat.sendMessage("Sorry, I don't know that command")

	def sendMessage(self, chat, message):
		self.bot.sendMessage(chat_id=chat.chat_id, text=message)

	def broadcastMessage(self,message):
		chats = Chat.objects.all()

		for chat in chats:
			chat.sendMessage(message)


class Chat(models.Model):
	chat_id = models.CharField(max_length=255, null=False, blank=False)
	manager = models.ForeignKey('TelegramManager', related_name='chats', blank=False, null=False)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=False) #Model must have 

	api_key = models.CharField(max_length=255, null=False, blank=False)

	def sendMessage(self,message):
		self.manager.sendMessage(self,message)

from django.db.models.signals import pre_save
from django.dispatch import receiver
from reversion.models import Revision

@receiver(pre_save, sender=Revision)
def my_handler(sender, **kwargs):
    print "I just got triggered"
