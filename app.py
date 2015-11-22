__author__ = 'cloudera'

from flask import Flask, jsonify, make_response, abort, request
import sqlite3
import itertools 
import os

app = Flask(__name__)
app.config.update(dict(DATABASE = os.path.join(app.root_path,'planetlabs.db')))

#######################################
# utility functions 
#######################################
def group_exists(group_list, valid_groups):
    ''' Checks if all groups in group_list exist in the database'''
    if len(group_list) > len(valid_groups):
        return False
    for group in group_list:
        if not group in valid_groups:
            return False
    return True

def user_record_is_valid(record):
    ''' Checks if record contains all fields '''
    if not record or (
            not 'userid' in record or
            not 'first_name' in record or
            not 'last_name' in record or
            not 'groups' in record):
        return False
    else:
        return True


def initiate_db():
    ''' creates database tables if not created at the start of the application ''' 
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()

    c.execute('PRAGMA foreign_keys=1;')
    # c.execute('INSERT INTO users VALUES(?,?,?)', record)
    # create tables: 
    c.execute('''CREATE TABLE IF NOT EXISTS users (first_name VARCHAR(20),
        last_name VARCHAR(20),
        userid VARCHAR(20) PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS groups (group_name VARCHAR(20) PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users_groups (userid VARCHAR(20), 
                group_name VARCHAR(20), 
                FOREIGN KEY (userid) REFERENCES users(userid) ON DELETE CASCADE, 
                FOREIGN KEY (group_name) REFERENCES groups(group_name) ON DELETE CASCADE);''')
    conn.commit()
    conn.close()

###############################################
# routes
###############################################    
@app.route('/users/<userid>', methods=['GET'])
def get_user(userid):
    ''' Returns the matching user record or 404 if none exist '''
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    try:
        c.execute('SELECT * FROM users WHERE userid = ?',[userid])
        user_record = c.fetchone()
        c.execute('SELECT group_name FROM users_groups WHERE userid = ?', [userid])
        users_groups_record = c.fetchall()
        group_names = []
        for record in users_groups_record:
            group_names.append(record[0])

        conn.close()
        print user_record
        return jsonify({'first_name': user_record[0],
            'last_name': user_record[1],
            'userid': user_record[2],
            'groups': group_names})
    except:
        abort(404)


@app.route('/users', methods=['POST'])
def create_user():
    '''Creates a new user record '''
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('SELECT * FROM groups')
    valid_groups = list(itertools.chain.from_iterable(c.fetchall()))
    
    # check validity of record:
    if not request.json or (
            not 'userid' in request.json or
            not 'first_name' in request.json or
            not 'last_name' in request.json or
            not 'groups' in request.json) or not group_exists(request.json['groups'], valid_groups):
        abort(400)

    # check if record already exists:
    #conn = sqlite3.connect('planetlabs.db')
    #c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE userid=?',[request.json['userid']])
    if c.fetchone()[0] > 0:
        #query_result = c.fetchone()[0]
        # userid already exists 
        conn.close()
        abort(403)
    else:
        new_user_record = [request.json['first_name'], request.json['last_name'], request.json['userid']]
        c.execute('INSERT INTO users VALUES (?, ?, ?)', new_user_record)
        for group_name in request.json['groups']:
            record = [request.json['userid'], group_name]
            c.execute('INSERT INTO users_groups VALUES(?, ?)', record)
        conn.commit()
        conn.close()
        return jsonify({'users': new_user_record}), 201

    

@app.route('/users/<userid>', methods=['DELETE'])
def delete_user(userid):
    '''Deletes a user record. Returns 404 if the user doesn't exist.'''
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE userid = ?', [userid])

    if c.fetchone()[0] == 0:
        conn.close()
        abort(404)
    else:
        c.execute('PRAGMA foreign_keys=1;')
        c.execute('DELETE FROM users WHERE userid=?', [userid])
        #c.execute('DELETE FROM users_groups WHERE userid=?', [userid])
        conn.commit()
        conn.close()
        return jsonify({"message": "delete success"})
 


@app.route('/users/<userid>', methods=['PUT'])
def update_user(userid):
    '''Updates an existing user record.'''
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    # check if userid exists
    c.execute('SELECT * FROM groups')
    valid_groups = list(itertools.chain.from_iterable(c.fetchall()))
    c.execute('SELECT COUNT(*) FROM users WHERE userid=?',[userid])
    if c.fetchone()[0] == 0:
        abort(404)
    else:
        # check if input is valid user record:
        if user_record_is_valid(request.json) and group_exists(request.json['groups'], valid_groups):
            c.execute('UPDATE users SET first_name=?, last_name=? WHERE userid=?', 
                        [request.json['first_name'], request.json['last_name'], userid])
            # update group associations by first deleting previous associations
            c.execute('DELETE FROM users_groups WHERE userid=?', [userid])
            for group_name in request.json['groups']:
                record = [userid, group_name]
                c.execute('INSERT INTO users_groups VALUES (?, ?)', record)
            conn.commit()
            conn.close()
            return jsonify({"message":"record updated"})
        else:
            abort(400)


@app.route('/groups/<group_name>', methods=['GET'])
def get_group(group_name):
    '''Returns a JSON list of userids containing the members of that group: {'userids':['user1', 'user2']}'''
    # check if the group_name exists
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('SELECT userid FROM users_groups WHERE group_name=?',[group_name])
    userids = c.fetchall()
    if userids is None or len(userids) == 0:
        abort(404)
    else:
        #userids = list(itertools.chain.from_iterable(c.fetchall()))
        userids_flattened = list(itertools.chain.from_iterable(userids))
        conn.close()
        return jsonify({'userids': userids_flattened})


@app.route('/groups', methods=['POST'])
def add_new_group():
    '''Creates a empty group.'''
    # check if group name already exists
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM groups WHERE group_name=?',[request.json['name']])
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO groups VALUES (?)', [request.json['name']])
        conn.commit()
        conn.close()
        return jsonify({'message':'new empty group added'})
    else:
        abort(403)



@app.route('/groups/<group_name>', methods=['PUT'])
def update_group(group_name):
    '''Updates the membership list for the group.'''
    # check if valid group name 
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM groups WHERE group_name=?',[group_name])
    if c.fetchone()[0] > 0:
        c.execute('DELETE FROM users_groups WHERE group_name=?', [group_name])
        for userid in request.json['userids']:
            c.execute('INSERT INTO users_groups VALUES (?, ?)',[userid, group_name])
        conn.commit()
        conn.close()
        return jsonify({'message': 'group memberships updated'})
    else:
        conn.close()
        abort(404)

@app.route('/groups/<group_name>', methods=['DELETE'])
def delete_group(group_name):
    ''' Deletes a group.'''
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM groups WHERE group_name=?',[group_name])
    if c.fetchone()[0] > 0:
        c.execute('PRAGMA foreign_keys=1;')        
        c.execute('DELETE FROM groups WHERE group_name=?', [group_name])
        conn.commit()
        conn.close()
        return jsonify({'message':'group deleted'})
    else:
        conn.close()
        abort(404)


###############################################
'''
# for testing purpose
@app.route('/users', methods=['GET'])
def display_users():
    return jsonify({'users': users})

@app.route('/groups', methods=['GET'])
def display_groups():
    return jsonify({'groups': groups})
'''
###############################################
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'not found'}), 404)

@app.errorhandler(403)
def forbidden(error):
    return make_response(jsonify({'error': 'record already exists! Forbidden!'}), 403)

@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'bad request'}), 400)

################################################


if __name__ == '__main__':
    initiate_db()
    app.run(debug=True)