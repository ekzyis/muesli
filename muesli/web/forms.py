# -*- coding: utf-8 -*-
#
# muesli/web/forms.py
#
# This file is part of MUESLI.
#
# Copyright (C) 2011, Ansgar Burchardt <ansgar (at) 43-1.org>
# Copyright (C) 2011, Matthias Kuemmerer <matthias (at) matthias-k.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import formencode
from formencode import validators

from muesli import models
from muesli import utils
from muesli.types import TutorialTime

def boolToValue(boolean):
	if boolean==True:
		return 1
	elif boolean==False:
		return 0
	elif boolean==None:
		return 'None'

def valueToBool(value):
	if value==1:
		return True
	if value==0:
		return False
	if value=='None':
		return None

class FormField(object):
	def __init__(self, name, label="", type="text", options=None,
		value=None, size=40, comment=None,
		validator=None, required=False,
		cols=64,
		rows=24,
		readonly=False):
		self.name = name
		self.label = label
		self.type = type
		self.options = options
		self.value = value
		self.size = size
		self.comment = comment
		self.validator = validator
		self.required = required
		self.cols = cols
		self.rows = rows
		self.readonly = readonly

class FileField(FormField):
	def __init__(self, name, growable=False, **kwargs):
		kwargs['type'] = 'file'
		FormField.__init__(self, name, **kwargs)
		self.growable = growable

class PasswordField(FormField):
	def __init__(self, name, **kwargs):
		kwargs['type'] = 'password'
		FormField.__init__(self, name, **kwargs)

class HiddenField(FormField):
	def __init__(self, name, **kwargs):
		kwargs['type'] = 'hidden'
		FormField.__init__(self, name, **kwargs)

class Form(object):
	def __init__(self, formfields, send="Senden", chained_validators=[]):
		self.formfields = formfields
		self.updateNames()
		self.chained_validators = chained_validators
		self.createSchema()
		self.errors = {}
		self.send=send
		self.message=""
	def createSchema(self):
		fields = self.formfields
		chained_validators = self.chained_validators
		class Schema(formencode.Schema):
			def __init__(self, *args, **kwargs):
				for field in fields:
					if field.validator:
						kwargs[field.name] = field.validator
					else:
						kwargs[field.name] = formencode.validators.UnicodeString()
					kwargs[field.name].not_empty = field.required
				if chained_validators:
					kwargs['chained_validators'] = chained_validators
				formencode.Schema.__init__(self, *args, **kwargs)
		self.formValidator = FormValidator(Schema())
	def updateNames(self):
		self.named_fields = {}
		for field in self.formfields:
			self.named_fields[field.name] = field
	def processPostData(self, postData):
		if self.formValidator.validate(postData):
			self.values = {}
			for name in self.named_fields:
				field = self.named_fields[name]
				if field.type in ['select', 'radio']:
					for option in field.options:
						if self.formValidator[name] == str(option[0]):
							field.value = option[0]
				else:
					field.value = self.formValidator[name]
				self.values[name] = field.value
			self.errors = self.formValidator.errors
			return True
		else:
			self.errors = self.formValidator.errors
			return False
	__getitem__ = lambda self, key: self.named_fields[key].value
	def __setitem__(self, key, value):
		self.named_fields[key].value=value

class FormValidator(object):
	def __init__(self, schema, obj=None, fields=[]):
		self.schema = schema
		self.value = {}
		if obj is not None:
			for f in fields:
				self.value[f] = getattr(obj, f)
	def validate(self, value):
		self.errors = {}
		try:
			self.value.update(self.schema.to_python(value))
			return True
		except formencode.Invalid as exc:
			self.errors = exc.unpack_errors()
		#for key, e in exc.error_dict.iteritems():
		#  self.errors[key] = e.msg
		#self.errors = exc.error_dict
			return False
	__getitem__ = lambda self, key: self.value.get(key, "")
	__contains__ = lambda self, key: key in self.value
	__iter__ = lambda self: self.value.iterkeys()
	iterkeys = __iter__
	iteritems = lambda self: self.value.iteritems()
	update = lambda self, *args, **kwargs: self.value.update(*args, **kwargs)
	def bind(self, obj, fields):
		"""
		Update fields in obj using submitted values.
		"""
		for f in fields:
			setattr(obj, f, self[f])

class ObjectForm(Form):
	def __init__(self, obj, formfields, send="Ändern", chained_validators=[]):
		Form.__init__(self, formfields, send=send, chained_validators=chained_validators)
		self.obj = obj
	def saveField(self, fieldName):
		setattr(self.obj, fieldName, self[fieldName])
	def saveValues(self):
		for name in self.named_fields:
			self.saveField(name)


class UserLogin(formencode.Schema):
	email = validators.String(not_empty=True)
	password = validators.String(not_empty=True)

class LectureEdit(ObjectForm):
	def __init__(self, request, lecture):
		self.request =  request
		formfields = [
			FormField('type',
			   label='Typ',
			   type='select',
			   options=[[type, utils.lecture_types[type]['name']] for type in utils.lecture_types],
			   value=lecture.type,
			   required=True),
			FormField('name',
			   label='Name',
			   type='text',
			   size=100,
			   value=lecture.name,
			   required=True),
			FormField('term',
			   label='Semester',
			   type='select',
			   options=utils.getTerms(),
			   value=lecture.term),
			FormField('lsf_id',
			   label='Veranstaltungsnummer',
			   type='text',
			   size=20,
			   value=lecture.lsf_id),
			FormField('lecturer',
			   label='Dozent',
			   type='text',
			   size=40,
			   value=lecture.lecturer),
			FormField('url',
			   label='Homepage',
			   size=100,
			   value=lecture.url),
			FormField('mode',
			   label='Anmeldemodus',
			   type='select',
			   options=utils.modes,
			   value=lecture.mode),
			FormField('minimum_preferences',
			   label=u'Minimum möglicher Termine',
			   size=5,
			   comment=u'Bei Präferenzenanmeldung: Studenten müssen mindestens an soviel Terminen können. (Leer: Defaultformel)',
			   value=lecture.minimum_preferences,
			   validator=validators.Int()),
			FormField('password',
			   label=u'Passwort für Übungsleiter',
			   size=40,
			   comment=u'Bei leerem Passwort keine Anmeldung als Übungsleiter möglich',
			   value=lecture.password),
			FormField('is_visible',
			   label='Sichtbar',
			   type='radio',
			   options=[[1, 'Ja'], [0, 'Nein']],
			   value=boolToValue(lecture.is_visible))
			]
		if request.permissionInfo.has_permission('change_assistant'):
			assistants = request.db.query(models.User).filter(models.User.is_assistant==1).order_by(models.User.last_name).all()
			formfields.append(
			  FormField('assistant',
			   label='Assistent',
			   type='select',
			   options=[[a.id, unicode(a)] for a in assistants],
			   value=lecture.assistant.id,
			   required=True,
			   ))
		ObjectForm.__init__(self, lecture, formfields, send=u'Ändern')
	def saveField(self, fieldName):
		if fieldName == 'is_visible':
			self.obj.is_visible = valueToBool(self['is_visible'])
		elif fieldName == 'assistant':
			assistant = self.request.db.query(models.User).get(self['assistant'])
			self.obj.assistant = assistant
		else:
			ObjectForm.saveField(self, fieldName)

class LectureAdd(ObjectForm):
	def __init__(self, request):
		self.request =  request
		formfields = [
			FormField('type',
			   label='Typ',
			   type='select',
			   options=[[type, utils.lecture_types[type]['name']] for type in utils.lecture_types],
			   #value=lecture.type,
			   required=True),
			FormField('name',
			   label='Name',
			   type='text',
			   size=100,
			   #value=lecture.name,
			   required=True),
			FormField('term',
			   label='Semester',
			   type='select',
			   options=utils.getTerms(),
			   #value=lecture.term
			   ),
			FormField('lsf_id',
			   label='Veranstaltungsnummer',
			   type='text',
			   size=20,
			   #value=lecture.lsf_id
			   ),
			FormField('lecturer',
			   label='Dozent',
			   type='text',
			   size=40,
			   #value=lecture.lecturer
			   ),
			FormField('url',
			   label='Homepage',
			   size=100,
			   #value=lecture.url
			   ),
			]
		if request.permissionInfo.has_permission('change_assistant'):
			assistants = request.db.query(models.User).filter(models.User.is_assistant==1).order_by(models.User.last_name).all()
			formfields.append(
			  FormField('assistant',
			   label='Assistent',
			   type='select',
			   options=[[a.id, unicode(a)] for a in assistants],
			   #value=lecture.assistant.id,
			   required=True,
			   ))
		ObjectForm.__init__(self, None, formfields, send=u'Anlegen')
	def saveField(self, fieldName):
		if fieldName == 'assistant':
			assistant = self.request.db.query(models.User).get(self['assistant'])
			self.obj.assistant = assistant
		else:
			ObjectForm.saveField(self, fieldName)

class UserEdit(ObjectForm):
	def __init__(self, request, user):
		formfields = [
			FormField('email',
			   label='E-Mail', size=40,
			   value=user.email,
			   required=True,
			   validator=validators.Email()),
			FormField('title',
			   label='Titel', size=20,
			   value=user.title),
			FormField('first_name',
			   label='Vorname', size=40,
			   value=user.first_name,
			   required=True),
			FormField('last_name',
			   label='Nachname', size=40,
			   value=user.last_name,
			   required=True),
			FormField('matrikel',
			   label='Matrikelnummer', size=10,
			   value=user.matrikel),
			FormField('subject',
			   label='Studiengang',
			   type='select',
			   value=user.subject,
			   options=utils.getSubjects(user)),
			FormField('subject_alt',
			   label='Studiengang', size=30, comment=u'Genauer Studiengang (falls Sonstiges gewählt)',
			   value=''),
			FormField('birth_date',
			   label='Geburtstag', size=10, comment='(TT.MM.JJJJ)',
			   value=user.birth_date),
			FormField('birth_place',
			   label='Geburtsort', size=20,
			   value=user.birth_place),
			FormField('is_assistant',
			   label='Assistent',
			   type='radio',
			   options=[[1, 'Ja'], [0, 'Nein']],
			   value=1 if user.is_assistant else 0),
			FormField('is_admin',
			   label='Admin',
			   type='radio',
			   options=[[1, 'Ja'], [0, 'Nein']],
			   value=1 if user.is_admin else 0)
			]
		ObjectForm.__init__(self, user, formfields, send=u'Änderungen übernehmen')
	def saveField(self, fieldName):
		if fieldName == 'subject':
			if self['subject']=='Sonstiges':
				self.obj.subject = self['subject_alt']
			else:
				self.obj.subject = self['subject']
		elif fieldName == 'alt_subject':
			pass
		else:
			ObjectForm.saveField(self, fieldName)

class UserUpdate(ObjectForm):
	def __init__(self, request, user):
		formfields = [
			FormField('email',
			   label='E-Mail', size=40,
			   value=user.email,
			   required=True,
			   validator=validators.Email()),
			FormField('title',
			   label='Titel', size=20,
			   value=user.title),
			FormField('first_name',
			   label='Vorname', size=40,
			   value=user.first_name,
			   required=True),
			FormField('last_name',
			   label='Nachname', size=40,
			   value=user.last_name,
			   required=True),
			FormField('matrikel',
			   label='Matrikelnummer', size=10,
			   value=user.matrikel),
			FormField('subject',
			   label='Studiengang',
			   type='select',
			   value=user.subject,
			   options=utils.getSubjects(user)),
			FormField('subject_alt',
			   label='Studiengang', size=30, comment=u'Genauer Studiengang (falls Sonstiges gewählt)',
			   value=''),
			FormField('birth_date',
			   label='Geburtstag', size=10, comment='(TT.MM.JJJJ)',
			   value=user.birth_date),
			FormField('birth_place',
			   label='Geburtsort', size=20,
			   value=user.birth_place),
			]
		ObjectForm.__init__(self, user, formfields, send=u'Änderungen übernehmen')
		self.editok = ['title', 'subject', 'subject_alt']
		for field in ['matrikel', 'birth_date', 'birth_place']:
			if not getattr(user, field):
				self.editok.append(field)
		for field in self.named_fields:
			if field not in self.editok:
				self.named_fields[field].readonly=True
	def saveField(self, fieldName):
		if fieldName not in self.editok:
			return
		if fieldName == 'subject':
			if self['subject']=='Sonstiges':
				self.obj.subject = self['subject_alt']
			else:
				self.obj.subject = self['subject']
		elif fieldName == 'alt_subject':
			pass
		else:
			ObjectForm.saveField(self, fieldName)

class UserRegister(ObjectForm):
	def __init__(self, request):
		formfields = [
			FormField('email',
			   label='E-Mail', size=40,
			   #value=user.email,
			   required=True,
			   validator=validators.Email()),
			FormField('title',
			   label='Titel', size=20,
			   #value=user.title
			   ),
			FormField('first_name',
			   label='Vorname', size=40,
			   #value=user.first_name,
			   required=True),
			FormField('last_name',
			   label='Nachname', size=40,
			   #value=user.last_name,
			   required=True),
			FormField('matrikel',
			   label='Matrikelnummer', size=10,
			   #value=user.matrikel,
			   required=True
			   ),
			FormField('subject',
			   label='Studiengang',
			   type='select',
			   #value=user.subject,
			   options=utils.getSubjects(),
			   required=True),
			FormField('subject_alt',
			   label='Studiengang', size=30, comment=u'Genauer Studiengang (falls Sonstiges gewählt)',
			   value=''),
			FormField('birth_date',
			   label='Geburtstag', size=10, comment='(TT.MM.JJJJ)',
			   #value=user.birth_date,
			   required=True
			   ),
			FormField('birth_place',
			   label='Geburtsort', size=20,
			   #value=user.birth_place,
			   required=True
			   )
			]
		ObjectForm.__init__(self, None, formfields, send=u'Registrieren')
	def saveField(self, fieldName):
		if fieldName == 'subject':
			if self['subject']=='Sonstiges':
				self.obj.subject = self['subject_alt']
			else:
				self.obj.subject = self['subject']
		elif fieldName == 'alt_subject':
			pass
		else:
			ObjectForm.saveField(self, fieldName)

class UserConfirm(ObjectForm):
	def __init__(self, request, confirmation):
		formfields = [
			FormField('email',
			   label='E-Mail', size=40,
			   readonly=True,
			   value=confirmation.user.email),
			PasswordField('password',
			   label='Passwort',
			   required=True
			   ),
			PasswordField('password_repeat',
			   label='Passwort (Wiederholung)',
			   required=True
			   ),
			HiddenField('hash',
			   value=confirmation.hash),
			]
		ObjectForm.__init__(self, None, formfields, send=u'Registrierung abschließen',
			chained_validators=[validators.FieldsMatch('password', 'password_repeat')])

class UserChangeEmail(ObjectForm):
	def __init__(self, request, user):
		formfields = [
			FormField('email',
			   label='E-Mail', size=40,
			   value=user.email,
			   required=True,
			   validator=validators.Email()),
			]
		ObjectForm.__init__(self, user, formfields, send=u'E-Mail-Adresse ändern')
	def saveField(self, fieldName):
		pass

class LectureAddExam(ObjectForm):
	def __init__(self, request):
		formfields = [
			FormField('name',
			   label='Name', size=100,
			   required=True),
			FormField('category',
			   label='Kategorie',
			   type='select',
			   options=[[cat['id'], cat['name']] for cat in utils.categories]),
			FormField('url',
			   label='URL', size=100)
			]
		ObjectForm.__init__(self, None, formfields, send=u'Anlegen')

class UserChangePassword(ObjectForm):
	def __init__(self, request):
		formfields = [
			PasswordField('old_password',
			   label='Altes Passwort', size=40,
			   required=True,
			   ),
			PasswordField('new_password',
			   label='Passwort',
			   required=True
			   ),
			PasswordField('new_password_repeat',
			   label='Passwort (Wiederholung)',
			   required=True
			   ),
			]
		ObjectForm.__init__(self, None, formfields, send=u'Neues Passwort setzen',
			chained_validators=[validators.FieldsMatch('new_password', 'new_password_repeat')])

class UserResetPassword(ObjectForm):
	def __init__(self, request):
		formfields = [
			FormField('email',
			   label='E-Mail', size=40,
			   required=True,
			   validator=validators.Email()),
			]
		ObjectForm.__init__(self, None, formfields, send=u'Passwort zurücksetzen')

class UserResetPassword3(ObjectForm):
	def __init__(self, request, confirmation):
		formfields = [
			FormField('email',
			   label='E-Mail', size=40,
			   readonly=True,
			   value=confirmation.user.email),
			PasswordField('password',
			   label='Passwort',
			   required=True
			   ),
			PasswordField('password_repeat',
			   label='Passwort (Wiederholung)',
			   required=True
			   ),
			]
		ObjectForm.__init__(self, None, formfields, send=u'Neues Passwort setzen',
			chained_validators=[validators.FieldsMatch('password', 'password_repeat')])

class LectureEditExam(ObjectForm):
	def __init__(self, request, exam):
		formfields = [
			FormField('name',
			   label='Name', size=100,
			   value=exam.name,
			   required=True),
			FormField('category',
			   label='Kategorie',
			   type='select',
			   value=exam.category,
			   options=[[cat['id'], cat['name']] for cat in utils.categories]),
			FormField('url',
			   value=exam.url,
			   label='URL', size=100),
			FormField('admission',
			   label='Zulassung',
			   type='radio',
			   value=boolToValue(exam.admission),
			   options=[[1, 'Editieren erlaubt'], [0, 'Editieren gesperrt'], ['None', 'Nicht notwendig']]),
			FormField('registration',
			   label='Anmeldung',
			   type='radio',
			   value=boolToValue(exam.registration),
			   options=[[1, 'Editieren erlaubt'], [0, 'Editieren gesperrt'], ['None', 'Nicht notwendig']]),
			]
		ObjectForm.__init__(self, exam, formfields, send=u'Änderungen speichern')
	def saveField(self, fieldName):
		if fieldName in ['admission', 'registration']:
			setattr(self.obj, fieldName, valueToBool(self[fieldName]))
		else:
			ObjectForm.saveField(self, fieldName)

class TutorialEdit(ObjectForm):
	def __init__(self, request, tutorial):
		# TODO: Übungsleiter angeben. Aber wurde das jemals genutzt?
		formfields = [
			#FormField('tutor',
			#   label=u'Übungsleiter', size=64),
			FormField('place',
			   label='Ort', size=64,
			   value=tutorial.place if tutorial else None,
			   required=True),
			FormField('wday',
			   label='Wochentag',
			   type='select',
			   options=list(enumerate(['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'])),
			   required=True,
			   value = int(tutorial.time.weekday()) if tutorial else None),
			FormField('timeofday',
			   label='Uhrzeit', size=5,
			   comment='(HH:MM oder HH)',
			   validator=validators.Regex(r'^[012]?[0-9](:[0-5][0-9])?$'),
			   required=True,
			   value=tutorial.time.time() if tutorial else None),
			FormField('max_students',
			   label='Max. Teilnehmerzahl', size=5,
			   validator=validators.Int,
			   required=True,
			   value=tutorial.max_students if tutorial else None),
			FormField('comment',
			   label='Kommentar', size=64,
			   value=tutorial.comment if tutorial else None),
			FormField('is_special',
			   label='Spezial',
			   type='radio',
			   options=[[1, 'Ja'], [0, 'Nein']],
			   value=boolToValue(tutorial.is_special) if tutorial else 0)
			]
		ObjectForm.__init__(self, tutorial, formfields, send=u'Ändern')
	def saveField(self, fieldName):
		if fieldName == 'is_special':
			setattr(self.obj, fieldName, valueToBool(self[fieldName]))
		elif fieldName == 'wday':
			pass
		elif fieldName == 'timeofday':
			timeofday = self['timeofday']
			if not ':' in timeofday:
				timeofday += ':00'
			if len(timeofday) <5:
				timeofday = '0' + timeofday
			timeString = '%s %s' % (self['wday'], timeofday)
			time = TutorialTime(timeString)
			setattr(self.obj, 'time', time)
		else:
			ObjectForm.saveField(self, fieldName)

class TutorialEmail(Form):
	def __init__(self):
		formfields = [
			FormField('subject',
			   label='Betreff', size=64,
			   required=True),
			FormField('body',
			   label='Nachricht', cols=64, rows=24,
			   type='textarea',
			   required=True),
			FileField('attachments',
			   label=u'Anhänge', size=64,
			   growable=False
			   ),
			FormField('copytome',
			   label=u'Kopie an mich',
			   type='radio',
			   options=list(enumerate([u'Senden', u'Nicht senden'])),
			   value=0
			   ),
			]
		Form.__init__(self, formfields, send=u'Senden')

class ExamAddOrEditExercise(ObjectForm):
	def __init__(self, request, exercise):
		formfields = [
			FormField('nr',
			   label='Nr.', size=4,
			   value=exercise.nr if exercise else None,
			   required=True,
			   validator=validators.Int()),
			FormField('maxpoints',
			   label='Punkte', size=4,
			   value=exercise.maxpoints if exercise else None,
			   # TODO: Nur eine Nachkommastelle erlaubt
			   validator=validators.Number(min=0),
			   required = True),
			]
		ObjectForm.__init__(self, exercise, formfields, send=u'Anlegen/Ändern')

class LectureAddGrading(ObjectForm):
	def __init__(self, request):
		formfields = [
			FormField('name',
			   label='Name', size=100,
			   required=True),
			]
		ObjectForm.__init__(self, None, formfields, send=u'Anlegen')

class LectureEmailTutors(Form):
	def __init__(self):
		formfields = [
			FormField('subject',
			   label='Betreff', size=64,
			   required=True),
			FormField('body',
			   label='Nachricht', cols=64, rows=24,
			   type='textarea',
			   required=True),
			FileField('attachments',
			   label=u'Anhänge', size=64,
			   growable=False
			   ),
			]
		Form.__init__(self, formfields, send=u'Senden')

class GradingEdit(ObjectForm):
	def __init__(self, request, grading):
		formfields = [
			FormField('name',
			   label='Name', size=100,
			   value=grading.name,
			   required=True),
			FormField('hispos_type',
			   label='Termin',
			   type='select',
			   options=[['01', 'Haupttermin'],['02', 'Nachtermin']],
			   value=grading.hispos_type),
			FormField('hispos_date',
			   label='Datum', size=10,
			   comment='(TT.MM.JJJJ)',
			   value=grading.hispos_date),
			FormField('examiner_id',
			   label=u'Prüfer-Id', size=10,
			   value=grading.examiner_id),
			]
		ObjectForm.__init__(self, grading, formfields, send=u'Ändern')