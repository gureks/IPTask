from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AdminPasswordChangeForm, PasswordChangeForm
from django.conf import settings
from django.http import HttpResponse

import time

from social_django.models import UserSocialAuth

import re
from twython import Twython
from textblob import TextBlob

import numpy as np
from PIL import Image
from os import path
import os
import matplotlib.pyplot as plt
import random

from wordcloud import WordCloud, STOPWORDS

import facebook
import requests

@login_required
def home(request):
	return render(request, 'home.html')


@login_required
def settings(request):
	user = request.user

	try:
		twitter_login = user.social_auth.get(provider='twitter')
	except UserSocialAuth.DoesNotExist:
		twitter_login = None

	try:
		facebook_login = user.social_auth.get(provider='facebook')
	except UserSocialAuth.DoesNotExist:
		facebook_login = None

	can_disconnect = False
	if user.social_auth.count() > 1 or user.has_usable_password():
		can_disconnect = True

	return render(request, 'settings.html', {
		'twitter_login': twitter_login,
		'facebook_login': facebook_login,
		'can_disconnect': can_disconnect
	})


@login_required
def password(request):
	if request.user.has_usable_password():
		PasswordForm = PasswordChangeForm
	else:
		PasswordForm = AdminPasswordChangeForm

	if request.method == 'POST':
		form = PasswordForm(request.user, request.POST)
		if form.is_valid():
			form.save()
			update_session_auth_hash(request, form.user)
			messages.success(request, 'Your password was successfully updated!')
			return redirect('password')
		else:
			messages.error(request, 'Please correct the error below.')
	else:
		form = PasswordForm(request.user)
	return render(request, 'password.html', {'form': form})

def grey_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
	return "hsl(0, 0%%, %d%%)" % random.randint(60, 100)

@login_required
def collect_tweets(request):
	user = request.user
	try:
		twitter_login = user.social_auth.get(provider='twitter')
	except UserSocialAuth.DoesNotExist:
		twitter_login = None

	if not twitter_login:
		return HttpResponse('''
				<meta http-equiv='refresh' content='3;url=/settings/' />
				You're not logged in via twitter. You'll be redirected to <a href='settings'>settings</a> to authorize twitter.
			''')

	twitter = Twython(
		'Gw5JZkQHAZiszoaw6FmYdauxL',
		'QfAsPGNGToPvCm3mj0Y2QTptDeSEEa3eUpFG8HnIjpoToo3KzM',
		twitter_login.extra_data['access_token']['oauth_token'],
		twitter_login.extra_data['access_token']['oauth_token_secret']
	)

	tweets = []
	text = ''
	try:
		search_data = twitter.get_user_timeline(user_id=twitter_login.extra_data['access_token']['screen_name'], count="100")
		data = search_data
		max_id = data[len(data)-1]['id']-1
		while True:
			print("Max ID - " + str(max_id) + " ---- Length of Data - " + str(len(data)))
			search_data = twitter.get_user_timeline(user_id=twitter_login.extra_data['access_token']['screen_name'], count="100", max_id=max_id)
			data.extend(search_data)
			previous_max_id = max_id
			max_id = data[len(data)-1]['id']-1
			if previous_max_id == max_id:
				break

		fetched_tweets = data

		for tweet in fetched_tweets:
			parsed_tweet = {}
			parsed_tweet['text'] = tweet['text']
			text += tweet['text']
			analysis = TextBlob(' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet['text']).split()))
			if analysis.sentiment.polarity > 0:
				parsed_tweet['sentiment'] = 'positive'
			elif analysis.sentiment.polarity == 0:
				parsed_tweet['sentiment'] = 'neutral'
			else:
				parsed_tweet['sentiment'] = 'negative'

			if tweet['retweet_count'] > 0:
				if parsed_tweet not in tweets:
					tweets.append(parsed_tweet)
			else:
				tweets.append(parsed_tweet)

		#Regex string and stopwords sourced from https://marcobonzanini.com/2015/03/09/mining-twitter-data-with-python-part-2/
		regex_str = [
			r'(?:[:=;][oO\-]?[D\)\]\(\]/\\OpP])', # Emoticons
			r'<[^>]+>', # HTML tags
			r'(?:@[\w_]+)', # @-mentions
			r"(?:\#+[\w_]+[\w\'_\-]*[\w_]+)", # hash-tags
			r'http[s]?://(?:[a-z]|[0-9]|[$-_@.&amp;+]|[!*\(\),]|(?:%[0-9a-f][0-9a-f]))+', # URLs
			r'(?:(?:\d+,?)+(?:\.?\d+)?)', # numbers
			r"(?:[a-z][a-z'\-_]+[a-z])", # words with - and '
			r'(?:[\w_]+)', # other words
			r'(?:U\+[a-zA-Z0-9]*)', #unicode chars
			r'(?:\S)' # anything else
		]
		tokens_regex =  re.compile(r'('+'|'.join(regex_str)+')', re.VERBOSE | re.IGNORECASE)
		tokenized_status = [term for term in tokens_regex.findall(text)]

		text = ' '.join(tokenized_status)

		stopwords = set(STOPWORDS)
		wc = WordCloud(max_words=1000, stopwords=stopwords, margin=10, random_state=1).generate(text)

		default_colors = wc.to_array()
		plt.imshow(wc.recolor(color_func=grey_color_func, random_state=3), interpolation="bilinear")
		wc.to_file('static/word_clouds/twitter_' + twitter_login.extra_data['access_token']['screen_name'] + '.png')
		return render(request, 'tweets.html', {
								'tweets': tweets,
								'image': 'word_clouds/twitter_' + twitter_login.extra_data['access_token']['screen_name'] + '.png',
								})

	except:
		print("Error tweet lene mei")
@login_required
def collect_fb(request):
	user = request.user
	try:
		facebook_login = user.social_auth.get(provider='facebook')
	except UserSocialAuth.DoesNotExist:
		facebook_login = None

	if not facebook_login:
		return HttpResponse('''
				<meta http-equiv='refresh' content='3;url=/settings/' />
				You're not logged in via Facebook. You'll be redirected to <a href='settings'>settings</a> to authorize facebook.
			''')

	data = list()
	text = ''

	graph = facebook.GraphAPI(access_token=facebook_login.extra_data['access_token'])
	posts = graph.get_connections(id='me', connection_name='posts')
	data.extend(posts['data'])
	while True:
		try:
			posts = requests.get(posts['paging']['next']).json()
			data.extend(posts['data'])
		except KeyError:
			break

	posts = []
	# try:
	for post in data:
		parsed_post = {}
		if 'story' in post.keys():
			parsed_post['message'] = post['story']
			analysis = TextBlob(' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", post['story']).split()))
			text += post['story']
		elif 'message' in post.keys():
			parsed_post['message'] = post['message']
			analysis = TextBlob(' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", post['message']).split()))
			text += post['message']
		else:
			parsed_post['message'] = None
			continue
		if analysis.sentiment.polarity > 0:
			parsed_post['sentiment'] = 'positive'
		elif analysis.sentiment.polarity == 0:
			parsed_post['sentiment'] = 'neutral'
		else:
			parsed_post['sentiment'] = 'negative'
		posts.append(parsed_post)

	#Regex string and stopwords sourced from https://marcobonzanini.com/2015/03/09/mining-twitter-data-with-python-part-2/
	regex_str = [
		r'(?:[:=;][oO\-]?[D\)\]\(\]/\\OpP])', # Emoticons
		r'<[^>]+>', # HTML tags
		r'(?:@[\w_]+)', # @-mentions
		r"(?:\#+[\w_]+[\w\'_\-]*[\w_]+)", # hash-tags
		r'http[s]?://(?:[a-z]|[0-9]|[$-_@.&amp;+]|[!*\(\),]|(?:%[0-9a-f][0-9a-f]))+', # URLs
		r'(?:(?:\d+,?)+(?:\.?\d+)?)', # numbers
		r"(?:[a-z][a-z'\-_]+[a-z])", # words with - and '
		r'(?:[\w_]+)', # other words
		r'(?:U\+[a-zA-Z0-9]*)', #unicode chars
		r'(?:\S)' # anything else
	]
	tokens_regex =  re.compile(r'('+'|'.join(regex_str)+')', re.VERBOSE | re.IGNORECASE)
	tokenized_status = [term for term in tokens_regex.findall(text)]

	text = ' '.join(tokenized_status)

	stopwords = set(STOPWORDS)
	filename = None
	if text:
		wc = WordCloud(max_words=1000, stopwords=stopwords, margin=10, random_state=1).generate(text)
		default_colors = wc.to_array()
		plt.imshow(wc.recolor(color_func=grey_color_func, random_state=3), interpolation="bilinear")
		filename = 'static/word_clouds/facebook_' + str(facebook_login) + '.png'
		wc.to_file(filename)

	return render(request, 'facebook.html', {
							'posts': posts,
							'image': filename,
							})

	# except:
	# 	print("Error facebook lene mei")
