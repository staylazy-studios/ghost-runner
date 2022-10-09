from GlobalInstance import GameObject as GI

class Timer:
    def __init__(self, seconds):
        self.startAt = GI['base'].taskMgr.globalClock.getFrameTime()
        self.pauseAt = self.startAt
        self.paused = False
        self.seconds = seconds
        self.initSeconds = seconds
    def reset(self, newTime=None):
        self.startAt = GI['base'].taskMgr.globalClock.getFrameTime()
        self.paused = False
        if newTime:
            self.seconds = newTime
        else:
            self.seconds = self.initSeconds
    def timeIsUp(self):
        if self.paused: return False
        ft = GI['base'].taskMgr.globalClock.getFrameTime()

        secNow = ft - self.startAt
        if secNow >= self.seconds:
            return True
        else:
            return False
    def pause(self):
        if self.paused: return
        self.pauseAt = GI['base'].taskMgr.globalClock.getFrameTime()
        self.paused = True
    def resume(self):
        if not self.paused: return
        resumeAt = GI['base'].taskMgr.globalClock.getFrameTime()
        self.seconds -= (self.pauseAt - self.startAt)
        self.startAt = resumeAt
        self.paused = False