# -*- coding: utf-8 -*-
# Adam Thompson 2018

import yaml
import os

class ConfigReader:

	def __init__(self, job_path):
		"""Initialize configReader class with a path to the root of the job"""
		self.job_path = job_path
		self.ymlFileName = "config.yml"
		self.configPath = os.path.join(self.job_path, self.ymlFileName)
		self.config = self.readConfig(self.configPath)
		self.tokenList = dict()
		self.tokenList['job_path'] = job_path

	def mergeDicts(self, x, y):
		"""Merges two dictionarys"""
		z = x.copy()
		z.update(y)
		return z

	def readConfig(self, configPath):
		"""Reads the config file and returns a dictionary"""
		with open(configPath) as stream:
			try:
				config = yaml.safe_load(stream)
			except yaml.YAMLError as exc:
				print(exc)
		return config

	def replaceTokens(self, templateString, tokenDict):
		"""Takes a templateString and attempts to create a path with a dictionary of tokens and values"""

		templateTokens = self.findTokens(templateString)
		formatedTemplateString = templateString
		for token in templateTokens:
			if token in self.tokenList:
				tokenSyntax = "<" + token + ">"
				# print("trying to replace " + token + " of this syntax: " + tokenSyntax + " with " + self.tokenList.get(token))
				# print("first it's this: " + templateString)
				formatedTemplateString = formatedTemplateString.replace(tokenSyntax, self.tokenList.get(token))
			else:
				raise ValueError("Missing token: " + token)
		return formatedTemplateString


	def getPath(self, template, tokenDict, destinationToken=None):
		"""Attempts to return the path to an optional destinationToken from the template and a dictionary of tokens"""
		self.tokenList = self.mergeDicts(self.tokenList, tokenDict)
		templateString = self.config[template]

		if (destinationToken != None):
			destinationToken = "<" + destinationToken + ">"
			tokenIndex = templateString.find(destinationToken)
			templateString = templateString[:tokenIndex]

		return self.replaceTokens(templateString, tokenDict)

	def getTokens(self, template):
		"""Returns a list of tokens in the given template minus the job path which is defined when configReader is created"""
		tokens = self.findTokens(self.config[template])
		tokens.remove('job_path')
		return tokens


	def findTokens(self, templateString):
		"""Finds tokens in a template and returns them in a list"""
		i = 0
		tokenList = list()
		while (i >= 0):
			i = templateString.find('<', i, len(templateString))
			if (i >= 0) : 
				start = i+1
				i = templateString.find('>', i, len(templateString))
				if (i > 0):
					end = i
					tokenList.append(templateString[start:end])
				else:
					break
			else: 
				break
		return tokenList

# DEBUG ------------------------------------------------------------------------------------------------------

# tokens = dict()
# tokens["job_path"] = "V:/Jobs/XXXXXX_thompsona_testJob"
# tokens["spot"] = "cool_spot"
# tokens["shot"] = "wow_such_shot"
# template = "nuke_projects"

# configReader = ConfigReader("V:/Jobs/XXXXXX_thompsona_testJob")

# try:
# 	fullPath = configReader.getPath(template, tokens, "shot")
# 	print(fullPath)
# 	print(configReader.getTokens(template))
# except ValueError as e:
# 	print(e)