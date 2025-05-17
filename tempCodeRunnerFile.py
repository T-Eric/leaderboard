class User(db.Model,UserMixin):
#     id=db.Column(db.Integer,primary_key=True)
#     name=db.Column(db.String(32))
#     password_hash=db.Column(db.String(32))
    
#     def set_password(self,password):
#         self.password_hash=generate_password_hash(password)
    
#     def validate_password(self,password):
#         return check_password_hash(self.password_hash,password) 
    
# class Model(db.Model):
#     id=db.Column(db.Integer,primary_key=True)
#     name=db.Column(db.String(32))
#     description=db.Column(db.String(128))
    
    
#     def add_submission(self,submission):
#         pass
    
    

# class Submission(db.Model):
#     pass