from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    role = Column(String(30), nullable=False, index=True)  # 'admin', 'professor', 'ta', 'student'
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    taught_courses = relationship("Course", back_populates="teacher")
    enrollments = relationship("Enrollment", back_populates="user", cascade="all, delete-orphan")
    submissions = relationship("Submission", foreign_keys="Submission.student_id", back_populates="student")
    graded_submissions = relationship("Submission", foreign_keys="Submission.graded_by_id", back_populates="graded_by")
    quiz_attempts = relationship("QuizAttempt", back_populates="student")
    resources = relationship("Resource", back_populates="owner")
    activity_logs = relationship("ActivityLog", back_populates="user")
    group_memberships = relationship("GroupMember", back_populates="user", cascade="all, delete-orphan")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)  # 'CS', 'EE', 'HCI', 'DS'
    name = Column(String(150), nullable=False)
    description = Column(Text, default="", nullable=False)
    head_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    courses = relationship("Course", back_populates="department")
    head = relationship("User", foreign_keys=[head_id])


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, default="", nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    department = relationship("Department", back_populates="courses")
    teacher = relationship("User", back_populates="taught_courses")
    sections = relationship("CourseSection", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="course", cascade="all, delete-orphan")
    resources = relationship("Resource", back_populates="course", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="course", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="course", cascade="all, delete-orphan")
    policies = relationship("CoursePolicy", back_populates="course", cascade="all, delete-orphan")
    discussion_threads = relationship("DiscussionThread", back_populates="course", cascade="all, delete-orphan")
    learning_modules = relationship("LearningModule", back_populates="course", cascade="all, delete-orphan")
    course_files = relationship("CourseFile", back_populates="course", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="course", cascade="all, delete-orphan")


class CourseSection(Base):
    __tablename__ = "course_sections"
    __table_args__ = (UniqueConstraint("course_id", "section_number", name="uq_course_section_number"),)

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    section_number = Column(String(20), nullable=False)  # 'SEC01', 'SEC02'
    title = Column(String(100), default="", nullable=False)
    room = Column(String(50), default="", nullable=False)
    meeting_times = Column(String(100), default="", nullable=False)
    capacity = Column(Integer, default=30, nullable=False)
    instructor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="sections")
    instructor = relationship("User", foreign_keys=[instructor_id])
    enrollments = relationship("Enrollment", back_populates="section")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_course_user_enrollment"),)

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey("course_sections.id", ondelete="SET NULL"), nullable=True)
    role = Column(String(30), default="student", nullable=False)  # 'student', 'ta', 'professor', 'coordinator', 'auditor'
    status = Column(String(20), default="active", nullable=False)  # 'active', 'suspended', 'revoked'
    enrolled_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="enrollments")
    user = relationship("User", back_populates="enrollments")
    section = relationship("CourseSection", back_populates="enrollments")


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="group")


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_user_membership"),)

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, default="", nullable=False)
    instructions = Column(Text, default="", nullable=False)
    due_date = Column(String(40), default="2026-12-15", nullable=False)
    max_grade = Column(Integer, default=100, nullable=False)
    submission_type = Column(String(30), default="text", nullable=False)
    is_group = Column(Boolean, default=False, nullable=False)
    allow_late = Column(Boolean, default=False, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student_submission"),)

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, default="", nullable=False)
    submitted_at = Column(DateTime(timezone=True), default=utc_now)
    status = Column(String(30), default="submitted", nullable=False)  # 'draft', 'submitted', 'graded'
    is_draft = Column(Boolean, default=False, nullable=False)
    extension_granted = Column(Boolean, default=False, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    grade = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    graded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    graded_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", foreign_keys=[student_id], back_populates="submissions")
    graded_by = relationship("User", foreign_keys=[graded_by_id], back_populates="graded_submissions")
    group = relationship("Group", back_populates="submissions")
    grade_history = relationship("GradeHistory", back_populates="submission", cascade="all, delete-orphan")


class GradeHistory(Base):
    __tablename__ = "grade_history"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    previous_grade = Column(Integer, nullable=True)
    new_grade = Column(Integer, nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at = Column(DateTime(timezone=True), default=utc_now)
    reason = Column(Text, default="", nullable=False)

    # Relationships
    submission = relationship("Submission", back_populates="grade_history")
    changed_by = relationship("User", foreign_keys=[changed_by_id])
    student = relationship("User", foreign_keys=[student_id])


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, default="", nullable=False)
    open_date = Column(String(40), default="2026-10-01", nullable=False)
    close_date = Column(String(40), default="2026-12-31", nullable=False)
    answer_release_date = Column(String(40), default="2026-12-31T23:59:59Z", nullable=False)
    time_limit_minutes = Column(Integer, default=30, nullable=False)
    max_attempts = Column(Integer, default=1, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="quizzes")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(30), default="multiple_choice", nullable=False)
    options_json = Column(Text, nullable=False)  # JSON array string e.g. ["Option A", "Option B"]
    correct_answer = Column(String(100), nullable=False)
    points = Column(Integer, default=10, nullable=False)

    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    answers = relationship("QuizAnswer", back_populates="question", cascade="all, delete-orphan")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (UniqueConstraint("quiz_id", "student_id", "attempt_number", name="uq_quiz_student_attempt_number"),)

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, default=1, nullable=False)
    started_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    score = Column(Integer, nullable=True)
    status = Column(String(30), default="finished", nullable=False)  # 'in_progress', 'finished'

    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    student = relationship("User", back_populates="quiz_attempts")
    answers = relationship("QuizAnswer", back_populates="attempt", cascade="all, delete-orphan")


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_quiz_answer_attempt_question"),)

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False)
    selected_option = Column(String(100), nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    points_awarded = Column(Integer, default=0, nullable=False)

    # Relationships
    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("QuizQuestion", back_populates="answers")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, default="", nullable=False)
    resource_type = Column(String(30), default="document", nullable=False)  # 'document', 'slides', 'link', 'pdf'
    url_or_content = Column(Text, default="", nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_visible = Column(Boolean, default=True, nullable=False)
    is_staff_only = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="resources")
    owner = relationship("User", back_populates="resources")


class CoursePolicy(Base):
    __tablename__ = "course_policies"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    policy_type = Column(String(50), nullable=False)  # 'institutional', 'grading', 'deadlines', 'quizzes'
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="policies")


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="announcements")
    author = relationship("User")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), nullable=True)
    role = Column(String(30), nullable=True)
    action = Column(String(50), nullable=False)  # 'VIEW', 'CREATE', 'UPDATE', 'DELETE', 'GRADE', 'SUBMIT', 'PUBLISH'
    resource_type = Column(String(50), nullable=False)  # 'course', 'gradebook', 'submission', 'quiz', 'admin', 'policy'
    resource_id = Column(String(50), nullable=True)
    outcome = Column(String(20), nullable=False)  # 'ALLOW', 'BLOCK'
    http_status = Column(Integer, nullable=False)
    detail = Column(Text, default="", nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    user = relationship("User", back_populates="activity_logs")


# ===================== NEW LMS MODULE MODELS =====================

class DiscussionThread(Base):
    __tablename__ = "discussion_threads"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)  # private staff-student thread
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="discussion_threads")
    author = relationship("User", foreign_keys=[author_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
    posts = relationship("DiscussionPost", back_populates="thread", cascade="all, delete-orphan")
    group = relationship("Group")


class DiscussionPost(Base):
    __tablename__ = "discussion_posts"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("discussion_threads.id", ondelete="CASCADE"), nullable=False)
    parent_post_id = Column(Integer, ForeignKey("discussion_posts.id", ondelete="CASCADE"), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    is_flagged = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    thread = relationship("DiscussionThread", back_populates="posts")
    parent_post = relationship("DiscussionPost", remote_side=[id], backref="replies")
    author = relationship("User", foreign_keys=[author_id])


class LearningModule(Base):
    __tablename__ = "learning_modules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, default="", nullable=False)
    order_index = Column(Integer, default=1, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)
    unlock_date = Column(String(40), default="", nullable=False)
    prerequisite_id = Column(Integer, ForeignKey("learning_modules.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="learning_modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")
    prerequisite = relationship("LearningModule", remote_side=[id])


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("learning_modules.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    content = Column(Text, default="", nullable=False)
    order_index = Column(Integer, default=1, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    module = relationship("LearningModule", back_populates="lessons")


class ModuleCompletion(Base):
    __tablename__ = "module_completions"
    __table_args__ = (UniqueConstraint("module_id", "student_id", name="uq_module_student_completion"),)

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("learning_modules.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    completed_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    module = relationship("LearningModule")
    student = relationship("User", foreign_keys=[student_id])


class CourseFile(Base):
    __tablename__ = "course_files"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    folder_path = Column(String(255), default="/", nullable=False)
    filename = Column(String(150), nullable=False)
    storage_path = Column(String(500), default="", nullable=False)
    mime_type = Column(String(100), default="application/octet-stream", nullable=False)
    file_size_bytes = Column(Integer, default=1024, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    access_level = Column(String(30), default="public", nullable=False)  # 'public', 'students', 'staff_only', 'group_only', 'private'
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    expires_at = Column(String(40), default="", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="course_files")
    owner = relationship("User", foreign_keys=[owner_id])
    group = relationship("Group")


class PeerReview(Base):
    __tablename__ = "peer_reviews"
    __table_args__ = (UniqueConstraint("submission_id", "reviewer_id", name="uq_submission_reviewer"),)

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_anonymous = Column(Boolean, default=True, nullable=False)
    review_text = Column(Text, default="", nullable=False)
    score = Column(Integer, nullable=True)
    status = Column(String(30), default="assigned", nullable=False)  # 'assigned', 'submitted', 'moderated'
    deadline = Column(String(40), default="", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    submission = relationship("Submission")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class GradeAppeal(Base):
    __tablename__ = "grade_appeals"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(30), default="pending", nullable=False)  # 'pending', 'under_review', 'approved', 'rejected'
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_notes = Column(Text, default="", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    submission = relationship("Submission")
    student = relationship("User", foreign_keys=[student_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey("course_sections.id", ondelete="SET NULL"), nullable=True)
    session_date = Column(String(40), nullable=False)
    title = Column(String(150), default="Lecture", nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course")
    section = relationship("CourseSection")
    created_by = relationship("User", foreign_keys=[created_by_id])
    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey("course_sections.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_date = Column(String(40), nullable=False)
    status = Column(String(30), default="present", nullable=False)  # 'present', 'absent', 'excused', 'late'
    is_locked = Column(Boolean, default=False, nullable=False)
    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, default="", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    course = relationship("Course", back_populates="attendance_records")
    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("User", foreign_keys=[student_id])
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])
