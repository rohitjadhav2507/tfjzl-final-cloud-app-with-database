from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.shortcuts import get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

# Import models
from .models import Course, Lesson, Enrollment, Question, Choice, Submission

# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        return Course.objects.order_by('-total_enrollment')[:10]


# CourseDetailView
class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = Enrollment.objects.filter(user=user, course=course).exists()
    if not is_enrolled:
        Enrollment.objects.create(user=user, course=course, mode='audit')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# Authentication Views
def registration_request(request):
    context = {}
    if request.method == 'POST':
        username = request.POST['username']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        password = request.POST['psw']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except Exception:
            pass

        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name, password=password)
            login(request, user)
            return HttpResponseRedirect(reverse(viewname='onlinecourse:index'))
        else:
            context = {"error": "User already exists."}
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)

    return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse(viewname='onlinecourse:index'))
        else:
            context = {"error": "Invalid username or password."}
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return HttpResponseRedirect(reverse(viewname='onlinecourse:index'))


# Helper method to extract answers
def extract_answers(request):
    submitted_answers = []
    for key, value in request.POST.items():
        if key.startswith('choice_'):
            try:
                submitted_answers.append(int(value))
            except ValueError:
                pass
        elif key == 'choice':
            for v in request.POST.getlist('choice'):
                try:
                    submitted_answers.append(int(v))
                except ValueError:
                    pass
    return submitted_answers


# Submit view
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    enrollment = Enrollment.objects.filter(user=user, course=course).first()
    if not enrollment:
        enrollment = Enrollment.objects.create(user=user, course=course, mode='honor')

    submission = Submission.objects.create(enrollment=enrollment)
    selected_choice_ids = extract_answers(request)
    submission.choices.set(selected_choice_ids)
    submission.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:show_exam_result', args=(course.id, submission.id,)))


# Exam result view
def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    selected_choices = submission.choices.all()
    selected_ids = [choice.id for choice in selected_choices]

    total_score = 0
    score = 0

    for question in course.question_set.all():
        total_score += question.grade
        if question.is_get_score(selected_ids):
            score += question.grade

    # Calculate grade as percentage score out of 100
    grade = int((score / total_score) * 100) if total_score > 0 else 0

    context = {
        'course': course,
        'submission': submission,
        'grade': grade,
        'score': score,
        'choices': selected_choices,
        'selected_ids': selected_ids,
    }
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
