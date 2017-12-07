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

		return render(request, 'tweets.html', {'tweets': tweets})

	except:
		print("Error tweet lene mei")
