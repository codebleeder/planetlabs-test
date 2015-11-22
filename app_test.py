import unittest
import app
import sqlite3
import json 

class AppTestCase(unittest.TestCase):
	def setUp(self):
		self.app = app.app.test_client()
		conn = sqlite3.connect('planetlabs.db')
		c = conn.cursor()
		c.execute('PRAGMA foreign_keys=1;')
		
		c.execute('DELETE FROM groups;')
		c.execute('DELETE FROM users;')
		# user 1
		c.execute('INSERT INTO users VALUES (?,?,?);',['John', 'Smith', 'jsmith'])
		c.execute('INSERT INTO groups VALUES (?);',['admins'])
		c.execute('INSERT INTO groups VALUES (?);',['users'])
		c.execute('INSERT INTO users_groups VALUES (?,?);',['jsmith', 'users']) 
		c.execute('INSERT INTO users_groups VALUES (?,?);',['jsmith', 'admins'])
		# user 2
		c.execute('INSERT INTO users VALUES (?,?,?);',['George', 'Martin', 'gmartin'])
		c.execute('INSERT INTO users_groups VALUES (?,?);',['gmartin', 'admins'])

		conn.commit()
		conn.close()

	def test_user_details(self):
		response = self.app.get('/users/jsmith')
		#print json.loads(response.data)
		#assert 'John' in rv.data
		#assert(response.status_code, 200)
		self.assertEqual(json.loads(response.data), {'first_name':'John', 'last_name':'Smith', 'userid': 'jsmith', 'groups':['users', 'admins']})

	def test_unknown_user_details(self):
		response = self.app.get('/users/ss')
		self.assertEqual(response.status_code, 404)

	def test_create_valid_user(self):
		response = self.app.post('/users', 
			data = json.dumps({'first_name': 'Sharad', 'last_name':'Shivmath', 'userid': 'ss', 'groups': ['admins']}),
			content_type = 'application/json')
		#assert(response.status_code, 200)
		response2 = self.app.get('/users/ss')
		print json.loads(response2.data)	
		self.assertEqual(json.loads(response2.data), {'first_name':'Sharad', 'last_name':'Shivmath', 'userid': 'ss', 'groups':['admins']})	

	def test_create_invalid_user(self):
		response = self.app.post('/users', 
			data = json.dumps({'first_name': 'Sharad', 'last_name':'Shivmath', 'groups': ['admins']}),
			content_type = 'application/json')
		self.assertEqual(response.status_code, 400) 

	def test_delete_known_user(self):
		response = self.app.delete('/users/jsmith')
		self.assertEqual(response.status_code, 200)

	def test_delete_unknown_user(self):
		response = self.app.delete('/users/ss')
		print 'delete unknown user:',response.status_code
		self.assertEqual(response.status_code, 404)

	def test_modify_known_user(self):
		response = self.app.put('/users/jsmith',
			data = json.dumps({'first_name': 'Johnny', 'last_name': 'Smithy', 'userid':'jsmith', 'groups':['admins', 'users']}))
		self.assertEqual(response.status_code, 400)

	def test_modify_unknown_user(self):
		response = self.app.put('/users/jsmit',
			data = json.dumps({'first_name': 'Johnny', 'last_name': 'Smithy', 'userid':'jsmith', 'groups':['admins', 'users']}))
		self.assertEqual(response.status_code, 404)

	def test_group_members(self):
		response = self.app.get('/groups/admins')
		#print response.data 
		self.assertEqual(json.loads(response.data),{'userids': ['jsmith','gmartin']})

	def test_invalid_group_name(self):
		response = self.app.get('/groups/designers')
		self.assertEqual(response.status_code, 404)

	def test_create_new_group(self):
		response = self.app.post('/groups', data = json.dumps({'name':'designers'}),
			content_type = 'application/json')
		print response.data
		self.assertEqual(response.status_code, 200)
		conn = sqlite3.connect('planetlabs.db')
		c = conn.cursor()
		c.execute('SELECT COUNT(*) FROM groups WHERE group_name = ?',['designers'])
		self.assertEqual(c.fetchone()[0], 1)
		conn.close()

	def test_try_to_create_old_group(self):
		response = self.app.post('/groups', data = json.dumps({'name':'admins'}),
			content_type = 'application/json')
		#print response.data
		self.assertEqual(response.status_code, 403)

	def test_update_group_membership(self):
		# add gmartin to users group
		response = self.app.put('/groups/users',
			data = json.dumps({'userids':['jsmith', 'gmartin']}),
			content_type = 'application/json')
		self.assertEqual(response.status_code, 200)
		response2 = self.app.get('/groups/users')
		self.assertEqual(json.loads(response2.data), {'userids':['jsmith', 'gmartin']})

	def test_delete_valid_group(self):
		response = self.app.delete('/groups/users')
		self.assertEqual(response.status_code, 200)
		response2 = self.app.get('/groups/users')
		self.assertEqual(response2.status_code, 404)

if __name__ == '__main__':
	unittest.main()
