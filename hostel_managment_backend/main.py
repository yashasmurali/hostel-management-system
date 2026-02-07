from fastapi import FastAPI
from pydantic import BaseModel
from database import get_connection
from fastapi.middleware.cors import CORSMiddleware
from mysql.connector import Error


app = FastAPI(title="MIT Hostel Solutions API")

# ✅ CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # or specify ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],   # allow all methods: GET, POST, PUT, DELETE
    allow_headers=["*"],   # allow all headers
)

# Pydantic model for JSON input
class WardenLogin(BaseModel):
    email: str
    password: str

@app.post("/warden-login")
def warden_login(credentials: WardenLogin):
    email = credentials.email
    password = credentials.password

    conn = get_connection()
    if conn is None:
        return {"status": "error", "message": "Database connection failed"}

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM warden WHERE email = %s AND password = %s", (email, password))
    warden = cursor.fetchone()

    cursor.close()
    conn.close()

    if not warden:
        return {"status": "error", "message": "Invalid email or password"}

    return {
        "status": "success",
        "message": f"Welcome {warden['name']}!",
        "warden": {
            "id": warden["warden_id"],
            "name": warden["name"],
            "email": warden["email"],
            "phone": warden["phone"]
        }
    }

class StudentInput(BaseModel):
    usn: str
    name: str
    student_mobile: str
    father_mobile: str
    mother_mobile: str
    email: str
    department_name: str
    year: int
    blood_group: str  # optional field


@app.post("/add-student")
def add_student(student: StudentInput):
    try:
        conn = get_connection()
        if conn is None:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor()

        default_password = student.usn
        room_status = "Pending"

        # ✅ Insert into student table
        query_student = """
            INSERT INTO student 
            (usn, name, student_mobile, father_mobile, mother_mobile, email, department_name, year, blood_group, password, room_allocation_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values_student = (
            student.usn,
            student.name,
            student.student_mobile,
            student.father_mobile,
            student.mother_mobile,
            student.email,
            student.department_name,
            student.year,
            student.blood_group,
            default_password,
            room_status
        )
        cursor.execute(query_student, values_student)

        # ✅ Automatically add entry to fees table (exclude 'pending' since it's generated)
        query_fee = """
            INSERT INTO fees (usn, name, total_fee, paid, status, due_date)
            VALUES (%s, %s, %s, %s, %s, NULL)
        """
        cursor.execute(query_fee, (student.usn, student.name, 0.00, 0.00, "Pending"))

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Student {student.name} added successfully!",
            "usn": student.usn,
            "default_password": default_password
        }

    except Error as e:
        return {"status": "error", "message": str(e)}

# ✅ Get all students with room & bed info (if allocated)
@app.get("/students")
def get_students():
    try:
        conn = get_connection()
        if conn is None:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                s.usn,
                s.name,
                s.student_mobile,
                s.father_mobile,
                s.mother_mobile,
                s.email,
                COALESCE(a.room_no, '—') AS room_no,
                COALESCE(a.bed_no, '—') AS bed_no,
                s.room_allocation_status
            FROM student s
            LEFT JOIN allocation a ON s.usn = a.usn
            ORDER BY s.usn ASC;
        """

        cursor.execute(query)
        students = cursor.fetchall()

        cursor.close()
        conn.close()

        if not students:
            return {"status": "success", "data": [], "message": "No students found"}

        return {"status": "success", "count": len(students), "data": students}

    except Error as e:
        return {"status": "error", "message": str(e)}


# ✅ Model for room input
class RoomInput(BaseModel):
    room_no: str
    no_of_beds: int
    no_of_tables: int
    no_of_chairs: int
    no_of_fans: int


# ✅ Add Room API (auto-create beds)
@app.post("/add-room")
def add_room(room: RoomInput):
    try:
        conn = get_connection()
        if conn is None:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor()

        # default: room is empty when created
        no_of_occupancy = 0

        # ---- 1️⃣ Insert Room Details ----
        query_room = """
            INSERT INTO room (room_no, no_of_beds, no_of_tables, no_of_chairs, no_of_fans, no_of_occupancy)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        room_values = (
            room.room_no,
            room.no_of_beds,
            room.no_of_tables,
            room.no_of_chairs,
            room.no_of_fans,
            no_of_occupancy
        )

        cursor.execute(query_room, room_values)

        # ---- 2️⃣ Auto Generate Beds for this Room ----
        bed_query = """
            INSERT INTO bed (room_no, bed_no, occupied_by)
            VALUES (%s, %s, %s)
        """

        for i in range(1, room.no_of_beds + 1):
            bed_no = i
            cursor.execute(bed_query, (room.room_no, bed_no, None))

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Room {room.room_no} added successfully with {room.no_of_beds} beds!",
            "room_details": {
                "room_no": room.room_no,
                "beds": room.no_of_beds,
                "tables": room.no_of_tables,
                "chairs": room.no_of_chairs,
                "fans": room.no_of_fans,
                "occupancy": no_of_occupancy
            }
        }

    except Error as e:
        return {"status": "error", "message": str(e)}



@app.get("/rooms")
def get_rooms():
    """
    Return all room details and a top summary using ONLY the `room` table.
    Vacancy = no_of_beds - no_of_occupancy (clamped to >= 0).
    """
    try:
        conn = get_connection()
        if conn is None:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor(dictionary=True)

        # Use the correct table name `room`
        query = """
            SELECT
                r.room_no,
                r.no_of_beds,
                r.no_of_tables,
                r.no_of_chairs,
                r.no_of_fans,
                r.no_of_occupancy,
                GREATEST(r.no_of_beds - r.no_of_occupancy, 0) AS vacant_beds
            FROM room r
            ORDER BY r.room_no ASC;
        """
        cursor.execute(query)
        rooms = cursor.fetchall()

        # compute summary
        total_rooms = len(rooms)
        total_beds = sum(r["no_of_beds"] for r in rooms) if rooms else 0
        total_occupied = sum(r["no_of_occupancy"] for r in rooms) if rooms else 0
        total_vacant = sum(r["vacant_beds"] for r in rooms) if rooms else 0

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "summary": {
                "total_rooms": total_rooms,
                "total_beds": total_beds,
                "occupied_beds": total_occupied,
                "vacant_beds": total_vacant
            },
            "rooms": rooms
        }

    except Error as e:
        return {"status": "error", "message": str(e)}


# ✅ Model for allocation input
class AllocationInput(BaseModel):
    usn: str
    room_no: str
    bed_no: str


# ✅ API: Allocate room + update all related tables
@app.post("/allocate-room")
def allocate_room(data: AllocationInput):
    try:
        conn = get_connection()
        if conn is None:
            return {"status": "error", "message": "Database connection failed"}
        cursor = conn.cursor()

        usn = data.usn
        room_no = data.room_no
        bed_no = data.bed_no

        # start transaction
        conn.start_transaction()

        # --- 1️⃣ Insert into allocation table ---
        insert_alloc = """
            INSERT INTO allocation (usn, room_no, bed_no)
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_alloc, (usn, room_no, bed_no))

        # --- 2️⃣ Update room table occupancy ---
        update_room = """
            UPDATE room
            SET no_of_occupancy = no_of_occupancy + 1
            WHERE room_no = %s
        """
        cursor.execute(update_room, (room_no,))

        # --- 3️⃣ Update student table status ---
        update_student = """
            UPDATE student
            SET room_allocation_status = 'Allocated'
            WHERE usn = %s
        """
        cursor.execute(update_student, (usn,))

        # --- 4️⃣ Update bed table (mark as occupied) ---
        update_bed = """
            UPDATE bed
            SET occupied_by = %s
            WHERE room_no = %s AND bed_no = %s
        """
        cursor.execute(update_bed, (usn, room_no, bed_no))

        # commit everything
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Student {usn} allocated Room {room_no}, Bed {bed_no} successfully!"
        }

    except Error as e:
        if conn:
            conn.rollback()
        return {"status": "error", "message": str(e)}


class AutoAllocInput(BaseModel):
    usn: str


@app.post("/auto-allocate")
def auto_allocate(data: AutoAllocInput):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        usn = data.usn

        # ✅ Step 1 — find first empty bed
        cursor.execute("SELECT room_no, bed_no FROM bed WHERE occupied_by IS NULL LIMIT 1")
        bed = cursor.fetchone()

        if not bed:
            return {"status": "error", "message": "No vacant beds available!"}

        room_no = bed["room_no"]
        bed_no = bed["bed_no"]

        # ✅ Step 2 — Insert allocation
        cursor.execute(
            "INSERT INTO allocation (usn, room_no, bed_no) VALUES (%s, %s, %s)",
            (usn, room_no, bed_no),
        )

        # ✅ Step 3 — Update room occupancy
        cursor.execute(
            "UPDATE room SET no_of_occupancy = no_of_occupancy + 1 WHERE room_no = %s",
            (room_no,),
        )

        # ✅ Step 4 — Update student status
        cursor.execute(
            "UPDATE student SET room_allocation_status = 'Allocated' WHERE usn = %s",
            (usn,),
        )

        # ✅ Step 5 — Update bed table (mark as occupied)
        cursor.execute(
            "UPDATE bed SET occupied_by = %s WHERE room_no = %s AND bed_no = %s",
            (usn, room_no, bed_no),
        )

        # ✅ just commit at end (no start_transaction)
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Auto allocated Student {usn} → Room {room_no}, Bed {bed_no}",
            "allocation": {"usn": usn, "room_no": room_no, "bed_no": bed_no},
        }

    except Error as e:
        if conn:
            conn.rollback()
        return {"status": "error", "message": str(e)}

@app.get("/available-rooms")
def available_rooms():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                room_no,
                no_of_beds,
                no_of_occupancy,
                (no_of_beds - no_of_occupancy) AS vacant_beds
            FROM room
            WHERE (no_of_beds - no_of_occupancy) > 0
            ORDER BY room_no ASC;
        """)
        rooms = cursor.fetchall()
        cursor.close()
        conn.close()

        # Add display string (ex: "3/4")
        for r in rooms:
            r["occupancy_status"] = f"{r['no_of_occupancy']}/{r['no_of_beds']}"

        return {
            "status": "success",
            "count": len(rooms),
            "available_rooms": rooms
        }

    except Error as e:
        return {"status": "error", "message": str(e)}

@app.get("/pending-students")
def pending_students():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT usn, name, student_mobile, father_mobile, mother_mobile, email
            FROM student
            WHERE room_allocation_status = 'Pending'
            ORDER BY usn ASC;
        """)

        students = cursor.fetchall()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "count": len(students),
            "pending_students": students
        }

    except Error as e:
        return {"status": "error", "message": str(e)}


class StudentLogin(BaseModel):
    email: str
    password: str

@app.post("/student-login")
def student_login(payload: StudentLogin):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT usn, name, email, password, room_allocation_status FROM student WHERE email=%s", (payload.email,))
        student = cursor.fetchone()
        cursor.close()
        conn.close()

        if not student or student["password"] != payload.password:
            return {"status": "error", "message": "Invalid email or password"}

        return {
            "status": "success",
            "student": {
                "usn": student["usn"],
                "name": student["name"],
                "email": student["email"],
                "room_allocation_status": student["room_allocation_status"]
            }
        }
    except Error as e:
        return {"status": "error", "message": str(e)}

@app.get("/student/{usn}")
def get_student(usn: str):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT s.usn, s.name, s.email, s.student_mobile, s.father_mobile, s.mother_mobile,
                   s.department_name, s.year, s.blood_group, s.room_allocation_status,
                   a.room_no, a.bed_no, a.start_date, a.end_date, a.fees_amount
            FROM student s
            LEFT JOIN allocation a ON s.usn = a.usn
            WHERE s.usn = %s;
        """, (usn,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return {"status": "error", "message": "Student not found"}

        return {"status": "success", "student": row}
    except Error as e:
        return {"status": "error", "message": str(e)}


class ChangePassword(BaseModel):
    email: str
    old_password: str
    new_password: str

@app.post("/student-change-password")
def change_student_password(data: ChangePassword):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT password FROM student WHERE email=%s", (data.email,))
        row = cursor.fetchone()

        if not row:
            cursor.close()
            conn.close()
            return {"status": "error", "message": "Student not found"}

        if row["password"] != data.old_password:
            cursor.close()
            conn.close()
            return {"status": "error", "message": "Old password incorrect"}

        cursor.execute("UPDATE student SET password=%s WHERE email=%s", (data.new_password, data.email))
        conn.commit()
        cursor.close()
        conn.close()

        return {"status": "success", "message": "Password updated successfully"}
    except Error as e:
        if conn: conn.rollback()
        return {"status": "error", "message": str(e)}


@app.get("/student-room/{usn}")
def student_room(usn: str):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # get student's room
        cursor.execute("SELECT room_no FROM allocation WHERE usn=%s", (usn,))
        alloc = cursor.fetchone()
        if not alloc:
            cursor.close(); conn.close()
            return {"status": "error", "message": "Student not allocated"}

        room_no = alloc["room_no"]

        # fetch room info
        cursor.execute("""
            SELECT room_no, no_of_beds, no_of_tables, no_of_chairs, no_of_fans, no_of_occupancy,
                   (no_of_beds - no_of_occupancy) AS available_beds
            FROM room WHERE room_no=%s;
        """, (room_no,))
        room = cursor.fetchone()
        cursor.close(); conn.close()

        if not room:
            return {"status": "error", "message": "Room not found"}

        room["capacity"] = room["no_of_beds"]
        room["occupied"] = room["no_of_occupancy"]
        room["available"] = room["available_beds"]
        return {"status": "success", "room_summary": room}
    except Error as e:
        return {"status": "error", "message": str(e)}

@app.get("/roommates/{usn}")
def roommates(usn: str):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # find room number
        cursor.execute("SELECT room_no FROM allocation WHERE usn=%s", (usn,))
        record = cursor.fetchone()
        if not record:
            cursor.close(); conn.close()
            return {"status": "error", "message": "Student not allocated"}

        room_no = record["room_no"]

        # fetch roommates
        cursor.execute("""
            SELECT s.usn, s.name, s.department_name, s.year, s.email, a.bed_no
            FROM allocation a
            JOIN student s ON a.usn = s.usn
            WHERE a.room_no=%s;
        """, (room_no,))
        all_students = cursor.fetchall()
        cursor.close(); conn.close()

        # remove self
        roommates = [r for r in all_students if r["usn"] != usn]

        return {
            "status": "success",
            "room_no": room_no,
            "count": len(roommates),
            "roommates": roommates
        }
    except Error as e:
        return {"status": "error", "message": str(e)}



class LeaveRequestInput(BaseModel):
    usn: str
    room_no: str
    from_date: str   # format: 'YYYY-MM-DD'
    to_date: str
    reason: str
    contact: str

@app.post("/apply-leave")
def apply_leave(data: LeaveRequestInput):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # default approval status
        approval_status = "Pending"

        query = """
            INSERT INTO leave_request (usn, room_no, from_date, to_date, reason, contact, warden_approval)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.usn,
            data.room_no,
            data.from_date,
            data.to_date,
            data.reason,
            data.contact,
            approval_status
        )

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Leave request submitted successfully from {data.from_date} to {data.to_date}!"
        }

    except Error as e:
        if conn: conn.rollback()
        return {"status": "error", "message": str(e)}

class ComplaintInput(BaseModel):
    usn: str
    room_no: str
    type: str           # e.g. "Electrical", "Water", "Cleaning", etc.
    description: str

@app.post("/apply-complaint")
def apply_complaint(data: ComplaintInput):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        default_status = "Pending"

        query = """
            INSERT INTO complaint (usn, room_no, type, description, status)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (data.usn, data.room_no, data.type, data.description, default_status)

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Complaint of type '{data.type}' submitted successfully!"
        }

    except Error as e:
        if conn: conn.rollback()
        return {"status": "error", "message": str(e)}


@app.get("/student-leaves/{usn}")
def get_student_leaves(usn: str):
    try:
        conn = get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT leave_id, usn, room_no, from_date, to_date, reason, contact, warden_approval, created_at
            FROM leave_request
            WHERE usn = %s
            ORDER BY leave_id DESC
        """
        cursor.execute(query, (usn,))
        leaves = cursor.fetchall()
        cursor.close()
        conn.close()

        if not leaves:
            return {"status": "success", "message": "No leave records found", "leaves": []}

        return {"status": "success", "count": len(leaves), "leaves": leaves}

    except Error as e:
        return {"status": "error", "message": str(e)}

@app.get("/student-complaints/{usn}")
def get_student_complaints(usn: str):
    try:
        conn = get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT complaint_id, usn, room_no, type, description, status, created_at
            FROM complaint
            WHERE usn = %s
            ORDER BY complaint_id DESC
        """
        cursor.execute(query, (usn,))
        complaints = cursor.fetchall()
        cursor.close()
        conn.close()

        if not complaints:
            return {"status": "success", "message": "No complaints found", "complaints": []}

        return {"status": "success", "count": len(complaints), "complaints": complaints}

    except Error as e:
        return {"status": "error", "message": str(e)}

@app.get("/leaves/pending")
def get_pending_leaves():
    try:
        conn = get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                l.leave_id,
                l.usn,
                s.name AS student_name,
                s.department_name,
                s.year,
                l.room_no,
                l.from_date,
                l.to_date,
                l.reason,
                l.contact,
                l.warden_approval,
                l.created_at
            FROM leave_request l
            JOIN student s ON l.usn = s.usn
            WHERE l.warden_approval = 'Pending'
            ORDER BY l.created_at DESC
        """
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return {"status": "success", "count": len(results), "pending_leaves": results}

    except Error as e:
        return {"status": "error", "message": str(e)}

@app.get("/complaints/unresolved")
def get_unresolved_complaints():
    try:
        conn = get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                c.complaint_id,
                c.usn,
                s.name AS student_name,
                s.department_name,
                s.year,
                c.room_no,
                c.type,
                c.description,
                c.status,
                c.created_at
            FROM complaint c
            JOIN student s ON c.usn = s.usn
            WHERE c.status != 'Resolved'
            ORDER BY c.created_at DESC
        """
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return {"status": "success", "count": len(results), "unresolved_complaints": results}

    except Error as e:
        return {"status": "error", "message": str(e)}


from fastapi import Body

@app.post("/leave/update-status")
def update_leave_status(
    leave_id: int = Body(..., example=3),
    new_status: str = Body(..., example="Approved")
):
    try:
        conn = get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}

        # only allow valid statuses
        if new_status not in ["Approved", "Rejected"]:
            return {"status": "error", "message": "Invalid status — use Approved or Rejected"}

        cursor = conn.cursor()
        query = "UPDATE leave_request SET warden_approval = %s WHERE leave_id = %s"
        cursor.execute(query, (new_status, leave_id))
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        conn.close()

        if affected == 0:
            return {"status": "error", "message": f"No leave found with ID {leave_id}"}

        return {
            "status": "success",
            "message": f"Leave ID {leave_id} updated to {new_status}"
        }

    except Error as e:
        return {"status": "error", "message": str(e)}

@app.post("/complaint/update-status")
def update_complaint_status(
    complaint_id: int = Body(..., example=7),
    new_status: str = Body(..., example="In Progress")
):
    try:
        conn = get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}

        valid_status = ["Pending", "In Progress", "Resolved"]
        if new_status not in valid_status:
            return {"status": "error", "message": f"Invalid status — use one of {valid_status}"}

        cursor = conn.cursor()
        query = "UPDATE complaint SET status = %s WHERE complaint_id = %s"
        cursor.execute(query, (new_status, complaint_id))
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        conn.close()

        if affected == 0:
            return {"status": "error", "message": f"No complaint found with ID {complaint_id}"}

        return {
            "status": "success",
            "message": f"Complaint ID {complaint_id} updated to {new_status}"
        }

    except Error as e:
        return {"status": "error", "message": str(e)}


from datetime import date
from pydantic import BaseModel, Field

# ✅ Model
from datetime import date

class NoticeInput(BaseModel):
    title: str = Field(..., example="Hostel Cleaning Schedule")
    description: str = Field(..., example="All students must vacate their rooms for cleaning on Sunday at 10 AM.")

@app.post("/notice/add")
def add_notice(notice: NoticeInput):
    try:
        conn = get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor()

        # ✅ Use correct column: date_posted
        query = """
            INSERT INTO notice (title, description, date_posted)
            VALUES (%s, %s, %s)
        """
        values = (notice.title, notice.description, date.today())

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": "Notice added successfully",
            "notice": {
                "title": notice.title,
                "description": notice.description,
                "date_posted": str(date.today())
            }
        }

    except Error as e:
        return {"status": "error", "message": str(e)}


@app.get("/notice/all")
def get_all_notices():
    try:
        conn = get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}

        cursor = conn.cursor(dictionary=True)

        # ✅ Use correct column name
        query = """
            SELECT notice_id, title, description, date_posted
            FROM notice
            ORDER BY date_posted DESC, notice_id DESC
        """
        cursor.execute(query)
        notices = cursor.fetchall()
        cursor.close()
        conn.close()

        if not notices:
            return {"status": "success", "message": "No notices found", "notices": []}

        return {
            "status": "success",
            "count": len(notices),
            "notices": notices
        }

    except Error as e:
        return {"status": "error", "message": str(e)}


@app.post("/fees/update-common-fee")
def update_common_fee(data: dict):
    total_fee = data.get("total_fee")

    if total_fee is None:
        return {"status": "error", "message": "total_fee is required"}

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # update all student fees at once
        query = "UPDATE fees SET total_fee = %s"
        cursor.execute(query, (total_fee,))
        conn.commit()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Hostel fee updated to ₹{total_fee} for all students"
        }

    except Error as e:
        return {"status": "error", "message": str(e)}

@app.post("/fees/update-due-date")
def update_due_date(data: dict):
    due_date = data.get("due_date")

    if not due_date:
        return {"status": "error", "message": "due_date is required in format YYYY-MM-DD"}

    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = "UPDATE fees SET due_date = %s"
        cursor.execute(query, (due_date,))
        conn.commit()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Due date updated to {due_date} for all students"
        }

    except Error as e:
        return {"status": "error", "message": str(e)}


@app.post("/fees/update-payment")
def update_payment(data: dict):
    usn = data.get("usn")
    payment_amount = data.get("payment_amount")

    if not usn or payment_amount is None:
        return {"status": "error", "message": "usn and payment_amount are required"}

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch current payment details
        cursor.execute("SELECT total_fee, paid FROM fees WHERE usn = %s", (usn,))
        record = cursor.fetchone()

        if not record:
            return {"status": "error", "message": f"No fee record found for USN {usn}"}

        total_fee = record["total_fee"]
        paid = record["paid"]

        new_paid = paid + payment_amount

        # Determine status
        if new_paid >= total_fee:
            status = "Paid"
            new_paid = total_fee
        elif new_paid > 0:
            status = "Partially Paid"
        else:
            status = "Pending"

        # Update table
        query = """
            UPDATE fees
            SET paid = %s, status = %s
            WHERE usn = %s
        """
        cursor.execute(query, (new_paid, status, usn))
        conn.commit()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Payment updated for {usn}",
            "updated": {
                "paid": new_paid,
                "status": status
            }
        }

    except Error as e:
        return {"status": "error", "message": str(e)}

@app.get("/fees/summary")
def get_fee_summary():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT COUNT(*) AS total_students,
                   SUM(total_fee) AS total_fee_to_collect,
                   SUM(paid) AS total_collected,
                   SUM(total_fee - paid) AS total_pending,
                   SUM(CASE WHEN status = 'Paid' THEN 1 ELSE 0 END) AS students_paid,
                   SUM(CASE WHEN status != 'Paid' THEN 1 ELSE 0 END) AS students_unpaid
            FROM fees
        """)
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "summary": {
                "total_students": result["total_students"] or 0,
                "total_fee_to_collect": result["total_fee_to_collect"] or 0,
                "total_collected": result["total_collected"] or 0,
                "total_pending": result["total_pending"] or 0,
                "students_paid": result["students_paid"] or 0,
                "students_unpaid": result["students_unpaid"] or 0
            }
        }

    except Error as e:
        return {"status": "error", "message": str(e)}


@app.post("/fees/student")
def get_student_fee(data: dict):
    usn = data.get("usn")
    if not usn:
        return {"status": "error", "message": "USN is required"}

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # safer LEFT JOIN (to avoid missing record issues)
        query = """
            SELECT 
                f.usn,
                COALESCE(s.name, f.name) AS name,
                f.total_fee,
                f.paid,
                f.pending,
                f.status,
                f.due_date
            FROM fees f
            LEFT JOIN student s ON f.usn = s.usn
            WHERE f.usn = %s
        """
        cursor.execute(query, (usn,))
        record = cursor.fetchone()

        cursor.close()
        conn.close()

        if not record:
            return {
                "status": "error",
                "message": f"No fee record found for student USN {usn}"
            }

        # return clean response
        return {
            "status": "success",
            "fee_details": {
                "usn": record["usn"],
                "name": record["name"],
                "total_fee": float(record["total_fee"] or 0),
                "paid": float(record["paid"] or 0),
                "pending": float(record["pending"] or 0),
                "status": record["status"] or "Pending",
                "due_date": str(record["due_date"]) if record["due_date"] else None
            }
        }

    except Error as e:
        return {"status": "error", "message": str(e).strip()}

@app.get("/fees/all")
def get_all_fees():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # join fees and student for complete info
        query = """
            SELECT 
                f.usn,
                COALESCE(s.name, f.name) AS name,
                s.department_name,
                s.year,
                f.total_fee,
                f.paid,
                f.pending,
                f.status,
                f.due_date
            FROM fees f
            LEFT JOIN student s ON f.usn = s.usn
            ORDER BY s.year, s.department_name, f.usn;
        """
        cursor.execute(query)
        records = cursor.fetchall()

        cursor.close()
        conn.close()

        if not records:
            return {"status": "error", "message": "No fee records found"}

        # format data for cleaner frontend
        data = [
            {
                "usn": row["usn"],
                "name": row["name"],
                "department": row["department_name"],
                "year": row["year"],
                "total_fee": float(row["total_fee"] or 0),
                "paid": float(row["paid"] or 0),
                "pending": float(row["pending"] or 0),
                "status": row["status"],
                "due_date": str(row["due_date"]) if row["due_date"] else None
            }
            for row in records
        ]

        return {
            "status": "success",
            "total_students": len(data),
            "fee_records": data
        }

    except Error as e:
        return {"status": "error", "message": str(e).strip()}

@app.get("/dashboard/summary")
def dashboard_summary():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # total students
        cursor.execute("SELECT COUNT(*) AS total_students FROM student;")
        total_students = cursor.fetchone()["total_students"]

        # occupied rooms
        cursor.execute("SELECT COUNT(*) AS occupied_rooms FROM room WHERE no_of_occupancy > 0;")
        occupied_rooms = cursor.fetchone()["occupied_rooms"]

        # vacant rooms
        cursor.execute("SELECT COUNT(*) AS vacant_rooms FROM room WHERE no_of_occupancy < no_of_beds;")
        vacant_rooms = cursor.fetchone()["vacant_rooms"]

        # pending complaints (fixed table name)
        cursor.execute("SELECT COUNT(*) AS pending_complaints FROM complaint WHERE status != 'Resolved';")
        pending_complaints = cursor.fetchone()["pending_complaints"]

        # pending leaves
        cursor.execute("SELECT COUNT(*) AS pending_leaves FROM leave_request WHERE warden_approval IN ('No', 'Pending');")
        pending_leaves = cursor.fetchone()["pending_leaves"]

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "dashboard_summary": {
                "total_students": total_students,
                "occupied_rooms": occupied_rooms,
                "vacant_rooms": vacant_rooms,
                "pending_complaints": pending_complaints,
                "pending_leaves": pending_leaves
            }
        }

    except Error as e:
        return {"status": "error", "message": str(e).strip()}


@app.get("/dashboard/recent-complaints")
def recent_complaints():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                c.usn,
                s.name,
                c.room_no,
                c.type,
                c.description,
                c.status
            FROM complaint c
            LEFT JOIN student s ON c.usn = s.usn
            ORDER BY c.complaint_id DESC
            LIMIT 4;
        """
        cursor.execute(query)
        complaints = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "recent_complaints": complaints
        }

    except Error as e:
        return {"status": "error", "message": str(e).strip()}

@app.get("/dashboard/recent-leaves")
def recent_leaves():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                l.usn,
                s.name,
                l.room_no,
                l.from_date,
                l.to_date,
                l.reason,
                l.warden_approval
            FROM leave_request l
            LEFT JOIN student s ON l.usn = s.usn
            ORDER BY l.leave_id DESC
            LIMIT 4;
        """
        cursor.execute(query)
        leaves = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "recent_leaves": leaves
        }

    except Error as e:
        return {"status": "error", "message": str(e).strip()}

@app.post("/complaint/active-count")
def get_active_complaint_count(data: dict):
    usn = data.get("usn")
    if not usn:
        return {"status": "error", "message": "USN is required"}

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT COUNT(*) AS active_complaints
            FROM complaint
            WHERE usn = %s AND status != 'Resolved';
        """
        cursor.execute(query, (usn,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        active_count = result["active_complaints"] or 0

        return {
            "status": "success",
            "usn": usn,
            "active_complaints": active_count
        }

    except Error as e:
        return {"status": "error", "message": str(e).strip()}


@app.post("/room/details")
def get_room_details(data: dict):
    room_no = data.get("room_no")
    if not room_no:
        return {"status": "error", "message": "room_no is required"}

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1️⃣ Fetch room details
        cursor.execute("""
            SELECT 
                room_no,
                no_of_beds,
                no_of_tables,
                no_of_chairs,
                no_of_fans,
                no_of_occupancy,
                (no_of_beds - no_of_occupancy) AS vacant_beds
            FROM room
            WHERE room_no = %s
        """, (room_no,))
        room = cursor.fetchone()

        if not room:
            cursor.close()
            conn.close()
            return {"status": "error", "message": f"No room found with room_no {room_no}"}

        # 2️⃣ Fetch students allocated in that room
        cursor.execute("""
            SELECT 
                s.usn,
                s.name,
                s.department_name,
                s.year,
                a.bed_no,
                a.start_date,
                a.end_date
            FROM allocation a
            JOIN student s ON a.usn = s.usn
            WHERE a.room_no = %s
        """, (room_no,))
        members = cursor.fetchall()

        # 3️⃣ Fetch available beds in that room
        cursor.execute("""
            SELECT bed_no 
            FROM bed 
            WHERE room_no = %s AND occupied_by IS NULL
        """, (room_no,))
        available_beds = [row["bed_no"] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "room_details": {
                "room_no": room["room_no"],
                "total_beds": room["no_of_beds"],
                "tables": room["no_of_tables"],
                "chairs": room["no_of_chairs"],
                "fans": room["no_of_fans"],
                "occupied_beds": room["no_of_occupancy"],
                "vacant_beds": room["vacant_beds"],
                "available_bed_numbers": available_beds,
                "members": members
            }
        }

    except Error as e:
        return {"status": "error", "message": str(e).strip()}

@app.post("/student/recent-leaves")
def get_recent_leaves(data: dict):
    usn = data.get("usn")
    if not usn:
        return {"status": "error", "message": "USN is required"}

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch latest leave requests for the student
        cursor.execute("""
            SELECT 
                leave_id,
                usn,
                room_no,
                from_date,
                to_date,
                reason,
                contact,
                warden_approval,
                created_at
            FROM leave_request
            WHERE usn = %s
            ORDER BY created_at DESC
            LIMIT 5
        """, (usn,))

        leaves = cursor.fetchall()

        cursor.close()
        conn.close()

        if not leaves:
            return {
                "status": "success",
                "message": "No leave requests found for this student",
                "recent_leaves": []
            }

        return {
            "status": "success",
            "usn": usn,
            "recent_leaves": leaves
        }

    except Error as e:
        return {"status": "error", "message": str(e).strip()}