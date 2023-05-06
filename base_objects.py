from GlobalInstance import GameObject as GI
from direct.actor.Actor import Actor
from direct.interval.LerpInterval import LerpPosInterval
from math import sin

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

class ShapeKeyActor:
    def __init__(self, actor, jointName, speed=0.2):
        self.actor = actor
        #print(self.actor.listJoints())
        self.joint = self.actor.controlJoint(None, "modelRoot", jointName)

        self.intervalOn = LerpPosInterval(
            self.joint,
            speed,
            (1, 0, 0),
            startPos=(0, 0, 0),
            blendType="noBlend",
            name="shape key on interval"+jointName,
        )
        self.intervalOff = self.joint.posInterval(
            speed,
            (0, 0, 0),
            startPos=(1, 0, 0),
            blendType="noBlend",
            name="shape key off interval"+jointName,
        )
    
    def playOn(self):
        self.intervalOff.finish()
        self.intervalOn.start()
    def playOff(self):
        self.intervalOn.finish()
        self.intervalOff.start()
    def isPlaying(self):
        return self.intervalOn.isPlaying() or self.intervalOff.isPlaying()

class Drawer(ShapeKeyActor):
    def __init__(self, actor, jointName, **kwargs):
        super().__init__(actor, jointName, **kwargs)

        self.on = False
    def toggle(self):
        self.on = not self.on
        if self.on:
            self.playOn()
        else:
            self.playOff()

class Radio(ShapeKeyActor):
    def __init__(self, actor, jointName, **kwargs):
        super().__init__(actor, jointName, **kwargs)

        self.sound = GI['base'].audio3d.loadSfx("stuck-on-you_nowlu.ogg")
        self.sound.setLoop(True)
        GI['base'].audio3d.attachSoundToObject(self.sound, self.actor)

        self.on = False

    def toggle(self):
        self.on = not self.on
        if self.on:
            self.playOn()
            self.sound.play()
        else:
            self.playOff()
            self.sound.stop()