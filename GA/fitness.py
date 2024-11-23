import json

from Constants.time_intervals import TimeIntervalConstant
from GA.chromosome import TimeTableGeneration
from Constants.constant import (
    PenaltyConstants,
    Defaults,
)
from Samples.samples import SubjectTeacherMap


class TimetableFitnessEvaluator:
    def __init__(
        self,
        timetable,
        all_sections,
        subject_teacher_mapping,
        available_classrooms,
        available_labs,
        classroom_capacity,
        section_student_strength,
        subject_quota_data,
        teacher_time_preferences,
        teacher_daily_workload,
        available_days = Defaults.working_days
    ):
        self.timetable = timetable
        self.available_days = available_days
        self.all_sections = all_sections
        self.subject_teacher_mapping = subject_teacher_mapping
        self.available_classrooms = available_classrooms
        self.available_labs = available_labs
        self.classroom_capacity = classroom_capacity
        self.section_student_strength = section_student_strength
        self.subject_quota_data = subject_quota_data
        self.teacher_time_preferences = teacher_time_preferences
        self.teacher_daily_workload = teacher_daily_workload


    def evaluate_timetable_fitness(self):
        total_fitness = 0  # todo: to remove this
        daily_section_fitness_scores = {}
        weekly_fitness_scores = {}
        current_week = 1

        for day_index in range(0, len(self.timetable), len(self.available_days)):
            weekly_fitness = 0
            weekly_label = f"Week {current_week}"
            for week_number, day_name in enumerate(self.available_days):
                week_day_key = f"{weekly_label} - {day_name}"
                if week_day_key not in self.timetable:
                    continue

                daily_schedule = self.timetable[week_day_key]
                daily_section_fitness_scores[week_day_key] = {}
                day_fitness = 0

                for section, section_schedule in daily_schedule.items():

                    section_fitness = Defaults.starting_section_fitness
                    teacher_time_slot_tracking = {}
                    classroom_time_slot_tracking = {}
                    teacher_workload_tracking = {}

                    for schedule_item in section_schedule:
                        assigned_teacher = schedule_item['teacher_id']
                        assigned_classroom = schedule_item['classroom_id']
                        assigned_time_slot = TimeIntervalConstant.time_mapping[schedule_item['time_slot']]
                        assigned_subject = schedule_item['subject_id']
                        section_strength = self.section_student_strength[section]

                        #todo: change this to teacher break maximizer check.

                        # if "Break" in assigned_time_slot:
                        #     continue

                        # Penalty1: Double teacher booking for same time slot
                        if (assigned_teacher, assigned_time_slot) in teacher_time_slot_tracking:
                            section_fitness -= PenaltyConstants.PENALTY_TEACHER_DOUBLE_BOOKED
                        else:
                            teacher_time_slot_tracking[(assigned_teacher, assigned_time_slot)] = section


                        # Penalty2: Double same classroom booking for same time slot
                        if (assigned_classroom, assigned_time_slot) in classroom_time_slot_tracking:
                            section_fitness -= PenaltyConstants.PENALTY_CLASSROOM_DOUBLE_BOOKED
                        else:
                            classroom_time_slot_tracking[(assigned_classroom, assigned_time_slot)] = section


                        # Penalty3: If a classroom allocated for a section is less then the class capacity.
                        if section_strength > self.classroom_capacity.get(assigned_classroom, Defaults.max_class_capacity):
                            section_fitness -= PenaltyConstants.PENALTY_OVER_CAPACITY


                        # Penalty4: If preferred time for teacher not given.
                        preferred_time_slots = self.teacher_time_preferences[assigned_teacher]

                        if assigned_time_slot not in preferred_time_slots:
                            section_fitness -= PenaltyConstants.PENALTY_UN_PREFERRED_SLOT

                        # To check if the teacher workload maximize with max work load possible
                        if assigned_teacher not in teacher_workload_tracking:
                            teacher_workload_tracking[assigned_teacher] = []
                        else:
                            teacher_workload_tracking[assigned_teacher].append(assigned_time_slot)

                    for teacher, times_assigned in teacher_workload_tracking.items():
                        if len(times_assigned) > self.teacher_daily_workload[teacher]:
                            section_fitness -= PenaltyConstants.PENALTY_OVERLOAD_TEACHER

                    daily_section_fitness_scores[week_day_key][section] = section_fitness
                    day_fitness += section_fitness

                weekly_fitness += day_fitness
                total_fitness += day_fitness

            weekly_fitness_scores[weekly_label] = weekly_fitness
            current_week += 1

        return total_fitness, daily_section_fitness_scores, weekly_fitness_scores


if __name__ == "__main__":
    total_sections = 6
    total_classrooms = 8
    total_labs = 3

    timetable_generator = TimeTableGeneration(
        teacher_subject_mapping=SubjectTeacherMap.subject_teacher_map,
        total_sections=total_sections,
        total_classrooms=total_classrooms,
        total_labs=total_labs
    )
    generated_timetables = timetable_generator.create_timetable(5)

    # print("Generated Timetable:")
    # print(json.dumps(generated_timetables, indent=4))
    fitness_evaluator = TimetableFitnessEvaluator(
        generated_timetables,
        timetable_generator.sections,
        SubjectTeacherMap.subject_teacher_map,
        timetable_generator.classrooms,
        timetable_generator.lab_classrooms,
        timetable_generator.room_capacity,
        timetable_generator.section_strength,
        timetable_generator.subject_quota_limits,
        timetable_generator.teacher_availability_preferences,
        timetable_generator.weekly_workload,
        Defaults.working_days
    )
    overall_fitness, section_fitness_data, weekly_fitness_data = fitness_evaluator.evaluate_timetable_fitness()
    with open("GA/chromosome.json", "w") as timetable_file:
        json.dump(generated_timetables, timetable_file, indent=4)

    fitness_output_data = {
        "overall_fitness": overall_fitness,
        "section_fitness_scores": section_fitness_data,
        "weekly_fitness_scores": weekly_fitness_data
    }

    with open("GA/fitness.json", "w") as fitness_scores_file:
        json.dump(fitness_output_data, fitness_scores_file, indent=4)

    print(f"Overall Fitness: {overall_fitness}")
    print("Timetable and fitness scores have been saved.")
