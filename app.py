from flask import Flask, render_template, redirect, request, flash
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime, timezone
from sqlalchemy import func, text


#Swally-Ometer 

app = Flask(__name__)
app.secret_key = "some_old_shite"
app.config["SQLALCHEMY_DATABASE_URI"]= "sqlite:///database.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db =SQLAlchemy(app)  

#Data class

class Drink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False, unique=True)
    alcohol_units =db.Column(db.Float, nullable=False)

    def __repr__ (self):
        return f"Drink {self.name}: {self.alcohol_units} units)"
    
class Sesh(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    def __repr__(self):
        return f"Date: {self.date}"
    


class SeshEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sesh_id = db.Column(db.Integer, db.ForeignKey("sesh.id", ondelete="CASCADE"), nullable=False)
    drink_id = db.Column(db.Integer, db.ForeignKey("drink.id", ondelete="RESTRICT"), nullable=False)
    servings = db.Column(db.Integer, nullable=False)

    drink = db.relationship("Drink")
    sesh= db.relationship("Sesh", backref="Entries")




#Routes

@app.route("/", methods=['GET', "POST"])
def index():
    if request.method == "POST":
        print("Creating new Shesh")
        new_sesh = Sesh()
        print(f"New shesh created{new_sesh.id}")
        db.session.add(new_sesh)
        db.session.commit()
        drinks = Drink.query.order_by(Drink.name.asc()).all()

        valid_entry = False    
        for drink in drinks:
            servings = request.form.get(drink.name)
            print(f"processing drink: {drink.name}, servings {servings}")
            if servings and int(int(servings) > 0):
                valid_entry = True
                sesh_entry =SeshEntry(
                    sesh_id=new_sesh.id,
                    drink_id= drink.id,
                    servings=int(servings)
                )
                db.session.add(sesh_entry)
                db.session.commit()

            if not valid_entry:
                return "Error: no valid servings provided", 400
               
            # return render_template("index.html",  drinks=drinks)  
            db.session.commit()
        return redirect("/")   
            



    else:

        seshes = Sesh.query.order_by(Sesh.date.desc()).all()
        drinks = Drink.query.order_by(Drink.name.asc()).all()
        sesh_data=[]

        for sesh in seshes:
            entries = SeshEntry.query.filter_by(sesh_id=sesh.id).all()
            drink_summary = {}
            total_units = 0

            for entry in entries:
                drink_name = entry.drink.name
                units = entry.drink.alcohol_units * entry.servings
                total_units += units
                drink_summary[drink_name] = {
                    "servings": entry.servings,
                    "units": units
                }
            
            sesh_data.append(
                {
                    "date": sesh.date,
                    "drinks": drink_summary,
                    "total_units": total_units,
                    "id": sesh.id
                }
            )
        
        return render_template("index.html", sesh_data=sesh_data, drinks=drinks)
   


#Deleter

@app.route("/delete/<int:id>")
def deleteid(id:int):
    sesh_to_delete = Sesh.query.get_or_404(id)
    try:
        SeshEntry.query.filter_by(sesh_id=sesh_to_delete.id).delete()
        db.session.delete(sesh_to_delete)
        db.session.commit()
        return redirect("/")
    except Exception as e:
        print(f"Error:{e}")
        return f"Error: {e}"
    
@app.route("/delete_drink/<int:drink_id>")
def delete_drink(drink_id:int):
    print("delete drink method called")
    
    in_sesh = SeshEntry.query.filter_by(drink_id=drink_id).first()
    if in_sesh:
        flash("This drink is already in at least one sesh. Delete sesh(es) first, then delete drink. ")
        print("Drink is associated with a session")
        return redirect("/edit_drinks")
    else:
        try:
            print("Drink is not associated with a session")
            drink = Drink.query.get_or_404(drink_id)
            db.session.delete(drink)
            db.session.commit()
            return redirect("/edit_drinks")
        except Exception as e:
            print(f"error {e}")
            return f"error{e}"

    
@app.route("/statistics", methods=["GET"]) 
def statistics():
    # total_units = (
    #     db.session.query(
    #         func.sum(SeshEntry.servings * Drink.alcohol_units)
    #     )
    #     .join(Drink)
    #     .scalar()
    # )
    # return render_template("statistics.html", total_units=total_units)

    time_now =datetime.now(timezone.utc)
    current_year = time_now.year
    current_month = time_now.month
    current_week = time_now.isocalendar()[1]
    
    # sql_month = text("""
    #     SELECT SUM(se.servings * d.alcohol_units)
    #     FROM sesh_entry se
    #     JOIN drink d ON se.drink_id = d.id
    #     WHERE EXTRACT (YEAR FROM date) = :year
    #     AND EXTRACT (MONTH FROM date) = :month
    # """)

    # sql_month = text("""
    #     SELECT SUM(se.servings * d.alcohol_units)
    #     FROM sesh_entry se
    #     JOIN drink d ON se.drink_id = d.id
    #     WHERE strftime('%Y', se.date) = :year
    #     AND strftime('%m', se.date) = :month
    # """)

    sql_month = text("""
        SELECT SUM(se.servings * d.alcohol_units)
        FROM sesh_entry se
        JOIN drink d ON se.drink_id = d.id
        JOIN sesh s ON se.sesh_id = s.id
        WHERE strftime('%Y', s.date) = :year
        AND strftime('%m', s.date) = :month
    """)

    # result_month = db.session.execute(sql_month, {"year": current_year, "month": current_month}).scalar()

    result_month = db.session.execute(sql_month,{"year": str(current_year), "month": f"{current_month:02d}"}).scalar()

    sql_tu = text("""
        SELECT SUM(se.servings * d.alcohol_units)
        FROM sesh_entry se
        JOIN drink d ON se.drink_id = d.id 

    """)
    result_tu =db.session.execute(sql_tu).scalar()


    return render_template("statistics.html", total_units = result_tu, month_units = result_month )





@app.route("/edit_drinks", methods=["GET", "POST"])
def edit_drinks():
    if request.method == "POST":
        drink_name = request.form.get("drink name")
        drink_units = request.form.get("alcohol units")
        new_drink =Drink(
            name= drink_name,
            alcohol_units=drink_units
        )
        db.session.add(new_drink)
        db.session.commit()
        print("post method")
        return redirect("/edit_drinks")  


    else:
        drinks = Drink.query.order_by(Drink.name.asc()).all()
        return render_template("edit_drinks.html", drinks=drinks)



#Set up default drinks
def initialise_default_drinks():
    defaults = [
        {"name": "Pints of Beer", "units": 2.3},
        {"name": "Glasses of Wine", "units": 2.3},
        {"name": "Whiskies (single)", "units": 1}

    ]
    for drink in defaults:
        if not Drink.query.filter_by(name=drink["name"]).first():
            db.session.add(Drink(name=drink["name"], alcohol_units=drink["units"]))
    db.session.commit()

#Initialise some entries for testing

def initialise_test_entries():
    sesh = Sesh()
    db.session.add(sesh)
    db.session.commit()


    beer_entry = SeshEntry()
    beer_entry.sesh_id = sesh.id
    beer_entry.drink_id = Drink.query.filter_by(name="Pints of Beer").first().id
    beer_entry.servings = 1

    wine_entry = SeshEntry()
    wine_entry.sesh_id = sesh.id
    wine_entry.drink_id = Drink.query.filter_by(name="Glasses of Wine").first().id
    wine_entry.servings = 3

   
    db.session.add(beer_entry)
    db.session.add(wine_entry)
    db.session.commit()




#Runner and debugger
if __name__ == "__main__":
    with app.app_context():

        db.create_all()

        initialise_default_drinks()
        # initialise_test_entries()
        print(SeshEntry.__tablename__)  # probably "sesh_entry"
        print(Drink.__tablename__) 

    app.run(debug=True)
