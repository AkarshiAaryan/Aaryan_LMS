from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# ===================== USER SCHEMAS =====================

class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=120)
    role: str = Field("student", pattern="^(admin|professor|teacher|ta|student)$")
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|professor|teacher|ta|student)$")
    is_active: Optional[bool] = None
    password: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ===================== COURSE SCHEMAS =====================

class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    description: str
    teacher_id: Optional[int] = None
    teacher_name: Optional[str] = None
    student_count: int = 0
    current_user_role: Optional[str] = None
    tas: Optional[List[str]] = []
    is_archived: bool = False
    created_at: Optional[datetime] = None


class CourseCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=20)
    title: str = Field(..., min_length=3, max_length=150)
    description: str = ""
    teacher_id: Optional[int] = None


class CourseUpdate(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    teacher_id: Optional[int] = None
    is_archived: Optional[bool] = None


class CourseArchive(BaseModel):
    is_archived: bool = True


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    user_id: int
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    status: Optional[str] = "active"
    section_id: Optional[int] = None
    enrolled_at: Optional[datetime] = None


class EnrollmentCreate(BaseModel):
    course_id: int
    user_id: int
    role: str = "student"
    status: str = "active"
    section_id: Optional[int] = None


class EnrollmentUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|suspended|revoked)$")
    section_id: Optional[int] = None


# ===================== GROUP SCHEMAS =====================

class GroupMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    user_id: int
    username: Optional[str] = None
    full_name: Optional[str] = None
    joined_at: Optional[datetime] = None


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    name: str
    members: Optional[List[GroupMemberOut]] = []
    created_at: Optional[datetime] = None


# ===================== ASSIGNMENT SCHEMAS =====================

class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    course_code: Optional[str] = None
    title: str
    description: str
    instructions: str
    due_date: str
    max_grade: int
    submission_type: str
    is_group: bool = False
    allow_late: bool = False
    is_published: bool = True
    is_archived: bool = False
    created_at: Optional[datetime] = None
    submission_count: Optional[int] = 0
    my_submission: Optional[Any] = None
    current_user_role: Optional[str] = None


class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str = ""
    instructions: str = ""
    due_date: str = "2026-12-15"
    max_grade: int = 100
    submission_type: str = "text"
    is_group: bool = False
    allow_late: bool = False
    is_published: bool = True


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    due_date: Optional[str] = None
    max_grade: Optional[int] = None
    submission_type: Optional[str] = None
    is_group: Optional[bool] = None
    allow_late: Optional[bool] = None
    is_published: Optional[bool] = None


# ===================== SUBMISSION SCHEMAS =====================

class SubmissionCreate(BaseModel):
    content: str = Field(..., min_length=1)
    is_draft: bool = False
    group_id: Optional[int] = None


class GradeHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    course_id: int
    student_id: int
    previous_grade: Optional[int] = None
    new_grade: int
    changed_by_id: Optional[int] = None
    changed_by_name: Optional[str] = None
    changed_at: Optional[datetime] = None
    reason: str


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    assignment_title: Optional[str] = None
    course_id: Optional[int] = None
    course_code: Optional[str] = None
    student_id: int
    student_name: Optional[str] = None
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    content: str
    submitted_at: Optional[datetime] = None
    status: str
    is_draft: bool = False
    extension_granted: bool = False
    is_published: bool = True
    is_locked: bool = False
    grade: Optional[float] = None
    max_grade: Optional[float] = 100
    feedback: Optional[str] = None
    graded_by_id: Optional[int] = None
    graded_by_name: Optional[str] = None
    graded_at: Optional[datetime] = None


class SubmissionGrade(BaseModel):
    grade: float = Field(..., ge=0)
    feedback: Optional[str] = ""
    reason: Optional[str] = "Standard assessment grading"
    is_published: bool = True


# ===================== QUIZ SCHEMAS =====================

class QuizQuestionOut(BaseModel):
    id: int
    quiz_id: int
    question_text: str
    question_type: str
    options: List[str]
    points: int


class QuizQuestionAdminOut(QuizQuestionOut):
    correct_answer: str


class QuizQuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1)
    question_type: str = Field("multiple_choice", pattern="^(multiple_choice|true_false|short_answer)$")
    options: Optional[List[str]] = None
    correct_answer: str
    points: int = 1


class QuizCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str = ""
    open_date: str
    close_date: str
    answer_release_date: Optional[str] = None
    time_limit_minutes: int = 30
    max_attempts: int = 1
    is_published: bool = True


class QuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    course_code: Optional[str] = None
    title: str
    description: str
    open_date: str
    close_date: str
    answer_release_date: Optional[str] = None
    time_limit_minutes: int
    max_attempts: int
    is_published: bool
    is_archived: bool = False
    created_at: Optional[datetime] = None
    question_count: int = 0
    my_attempts_count: Optional[int] = 0
    attempts_remaining: Optional[int] = None
    questions: Optional[List[QuizQuestionOut]] = None
    current_user_role: Optional[str] = None


class QuizAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    quiz_title: Optional[str] = None
    course_code: Optional[str] = None
    student_id: int
    student_name: Optional[str] = None
    attempt_number: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    score: Optional[int] = None
    max_score: Optional[int] = 100
    status: str


class QuizAnswerSubmission(BaseModel):
    question_id: int
    selected_option: Optional[str] = None
    selected_answer: Optional[str] = None


class QuizSubmitRequest(BaseModel):
    answers: List[QuizAnswerSubmission]


# ===================== GRADEBOOK SCHEMAS =====================

class GradeItem(BaseModel):
    id: int
    item_type: str  # 'assignment' or 'quiz'
    item_title: str
    course_id: int
    course_code: str
    score: Optional[int] = None
    max_score: int
    status: str
    is_published: bool = True
    feedback: Optional[str] = None
    date: Optional[str] = None


class StudentGradebookRow(BaseModel):
    student_id: int
    student_name: str
    username: str
    grades: List[GradeItem]
    total_score: int
    max_total_score: int
    percentage: float


class PublishGradesRequest(BaseModel):
    is_published: bool = True


# ===================== RESOURCE SCHEMAS =====================

class ResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    course_code: Optional[str] = None
    title: str
    description: str
    resource_type: str
    url_or_content: str
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    is_visible: bool
    is_staff_only: bool = False
    created_at: Optional[datetime] = None


class ResourceCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: str = ""
    resource_type: str = "document"
    url_or_content: str = ""
    is_visible: bool = True
    is_staff_only: bool = False


# ===================== POLICY SCHEMAS =====================

class CoursePolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    policy_type: str
    title: str
    content: str
    created_at: Optional[datetime] = None


class CoursePolicyCreate(BaseModel):
    policy_type: str
    title: str
    content: str


# ===================== ANNOUNCEMENT SCHEMAS =====================

class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    course_code: Optional[str] = None
    title: str
    content: str
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    created_at: Optional[datetime] = None


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    content: str = Field(..., min_length=2)


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=150)
    content: Optional[str] = Field(None, min_length=2)


# ===================== LOGS & ADMIN STATS =====================

class ActivityLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    outcome: str
    http_status: int
    detail: str
    timestamp: Optional[datetime] = None


class AdminStatsOut(BaseModel):
    total_users: int
    total_students: int
    total_teachers: int
    total_courses: int
    total_enrollments: int
    total_submissions: int
    total_quiz_attempts: int
    recent_activity_count: int


# ===================== DEPARTMENT & SECTION SCHEMAS =====================

class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str
    head_id: Optional[int] = None
    head_name: Optional[str] = None
    created_at: Optional[datetime] = None


class DepartmentCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=20)
    name: str = Field(..., min_length=3, max_length=150)
    description: str = ""
    head_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    head_id: Optional[int] = None


class CourseSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    section_number: str
    title: str
    room: Optional[str] = ""
    meeting_times: Optional[str] = ""
    capacity: Optional[int] = 30
    instructor_id: Optional[int] = None
    instructor_name: Optional[str] = None
    created_at: Optional[datetime] = None


class CourseSectionCreate(BaseModel):
    section_number: str = Field(..., min_length=2, max_length=20)
    title: str = ""
    room: str = ""
    meeting_times: str = ""
    capacity: int = 30
    instructor_id: Optional[int] = None


# ===================== DISCUSSION FORUM SCHEMAS =====================

class DiscussionPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: int
    parent_post_id: Optional[int] = None
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    content: str
    is_flagged: bool
    created_at: Optional[datetime] = None


class DiscussionPostCreate(BaseModel):
    content: str = Field(..., min_length=1)
    parent_post_id: Optional[int] = None


class DiscussionPostUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class DiscussionThreadPin(BaseModel):
    is_pinned: bool = True


class DiscussionThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    recipient_id: Optional[int] = None
    recipient_name: Optional[str] = None
    title: str
    content: str
    is_pinned: bool
    is_locked: bool
    is_private: bool
    group_id: Optional[int] = None
    post_count: int = 0
    created_at: Optional[datetime] = None
    posts: Optional[List[DiscussionPostOut]] = []


class DiscussionThreadCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    content: str = Field(..., min_length=3)
    is_private: bool = False
    recipient_id: Optional[int] = None
    group_id: Optional[int] = None


# ===================== LEARNING MODULE SCHEMAS =====================

class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: int
    title: str
    content: str
    order_index: int
    is_published: bool
    created_at: Optional[datetime] = None


class LessonCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    content: str = ""
    order_index: int = 1
    is_published: bool = True


class LearningModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    description: str
    order_index: int
    is_published: bool
    unlock_date: str
    prerequisite_id: Optional[int] = None
    prerequisite_title: Optional[str] = None
    created_at: Optional[datetime] = None
    lessons: Optional[List[LessonOut]] = []


class LearningModuleCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str = ""
    order_index: int = 1
    is_published: bool = True
    unlock_date: str = ""
    prerequisite_id: Optional[int] = None


# ===================== COURSE FILE SCHEMAS =====================

class CourseFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    folder_path: str
    filename: str
    file_size_bytes: int
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    access_level: str
    group_id: Optional[int] = None
    is_archived: bool
    expires_at: str
    mime_type: Optional[str] = "application/octet-stream"
    created_at: Optional[datetime] = None


class CourseFileCreate(BaseModel):
    folder_path: str = "/"
    filename: str = Field(..., min_length=1, max_length=150)
    file_size_bytes: int = 1024
    access_level: str = "public"
    group_id: Optional[int] = None
    expires_at: str = ""


class CourseFileArchive(BaseModel):
    is_archived: bool = True


# ===================== PEER REVIEW & APPEAL SCHEMAS =====================

class PeerReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    assignment_title: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewer_name: Optional[str] = None
    is_anonymous: bool
    review_text: str
    score: Optional[int] = None
    status: str
    deadline: str
    created_at: Optional[datetime] = None


class PeerReviewSubmit(BaseModel):
    review_text: str = Field(..., min_length=5)
    score: int = Field(..., ge=0, le=100)


class PeerReviewAssign(BaseModel):
    submission_id: int
    reviewer_id: int
    is_anonymous: bool = True
    deadline: str = ""


class GradeAppealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    assignment_title: Optional[str] = None
    student_id: int
    student_name: Optional[str] = None
    reason: str
    status: str
    reviewer_id: Optional[int] = None
    reviewer_name: Optional[str] = None
    resolution_notes: str
    created_at: Optional[datetime] = None


class GradeAppealCreate(BaseModel):
    submission_id: Optional[int] = None
    reason: str = Field(..., min_length=5)


class GradeAppealResolve(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected|under_review)$")
    resolution_notes: str = Field(..., min_length=5)
    adjusted_grade: Optional[float] = None


# ===================== ATTENDANCE SCHEMAS =====================

class AttendanceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    section_id: Optional[int] = None
    session_id: Optional[int] = None
    student_id: int
    student_name: Optional[str] = None
    session_date: str
    status: str
    is_locked: bool
    recorded_by_id: Optional[int] = None
    recorded_by_name: Optional[str] = None
    notes: str
    created_at: Optional[datetime] = None


class AttendanceRecordCreate(BaseModel):
    student_id: int
    session_date: str
    section_id: Optional[int] = None
    session_id: Optional[int] = None
    status: str = Field("present", pattern="^(present|absent|excused|late)$")
    notes: str = ""


class AttendanceSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    section_id: Optional[int] = None
    session_date: str
    title: str
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None


class AttendanceSessionCreate(BaseModel):
    session_date: str
    title: str = "Lecture"
    section_id: Optional[int] = None
