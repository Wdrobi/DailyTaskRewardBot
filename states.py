from aiogram.fsm.state import State, StatesGroup


class TaskStates(StatesGroup):
    active_task = State()   # যেকোনো claimable task progress


class WithdrawalStates(StatesGroup):
    selecting_method  = State()  # পেমেন্ট মেথড বাছাই
    entering_number   = State()  # অ্যাকাউন্ট নম্বর লিখছেন
    confirming        = State()  # নিশ্চিত করছেন


class AdminStates(StatesGroup):
    broadcasting = State()   # ব্রডকাস্ট মেসেজ লিখছেন
    banning      = State()   # ব্যান করার জন্য আইডি লিখছেন
    unbanning    = State()   # আনব্যান করার জন্য আইডি লিখছেন
