from panda3d.core import loadPrcFileData

conf = """
win-size 1280 720
win-fixed-size 1
window-title Ghost Runner
show-frame-rate-meter 1
textures-power-2 none
#fullscreen true
#framebuffer-srgb 1
"""

loadPrcFileData("", conf)

from panda3d.core import WindowProperties, ModifierButtons, \
    PointLight, AmbientLight, \
    CollisionTraverser, CollisionHandlerQueue, CollisionHandlerPusher, CollisionNode, CollisionPolygon, CollisionRay, CollisionSegment, CollisionSphere, CollideMask, \
    GeomVertexFormat, NodePath, Point3, \
    TransparencyAttrib
from panda3d.ai import AIWorld, AICharacter
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage
from direct.interval.LerpInterval import LerpPosInterval
from direct.actor.Actor import Actor
from direct.showbase import Audio3DManager
from base_objects import *
import GlobalInstance
from wezupath import NavGraph, PathFollower
from random import choice, random
import sys



# Controls are:
# Move around - wasd (hold shift to run)
# Look around - with the goddamn mouse
# Turn flash light on - right click
# Hide/interact with objects - e
# Also some extra DEBUG controls are:
# 't' to teleport to a random enemy spawn point
# 'q' to make enemy chase you
# 'f' to .stash() player colNode
# 'f11' to fullscreen
# 'escape' to quit


USE_RP = True

if USE_RP:
    #pipeline_path = "/home/joey/dev/panda_3d/RenderPipeline/"
    pipeline_path = "render_pipeline/"
    sys.path.insert(0, pipeline_path)
    if pipeline_path == "render_pipeline/":
        from panda3d import _rplight as _
        import socket as _
        from rpcore import RenderPipeline, PointLight, SpotLight
        from direct.gui.DirectCheckBox import DirectCheckBox as _
        from direct.stdpy.file import isfile as _ # for rp
        from datetime import datetime as _
        # Plugins for packaging
    else:
        from rpcore import RenderPipeline, PointLight, SpotLight
    simplepbr = None
else:
    from panda3d.core import PointLight, Spotlight, PerspectiveLens
    import simplepbr
    #RenderPipeline = SpotLight = None

PLAYER_SPEED = 4
ENEMY_SPEED = 5
ENEMY_FOV = 70
CAMERA_HEIGHT = 3
CAMERA_FOV = 90

class Game(ShowBase):
    def __init__(self):
        if USE_RP:
            #super().__init__()
            # ----- Begin of render pipeline code -----
            self.render_pipeline = RenderPipeline()
            self.render_pipeline.create(self)

            #self.render_pipeline.daytime_mgr.time = "20:40"
            self.render_pipeline.daytime_mgr.time = "00:00"
            #self.render_pipeline.daytime_mgr.time = "7:40"
            # ----- End of render pipeline code -----'''
        else:
            super().__init__()
            self.setBackgroundColor(0, 0, 0, 0)
            self.pipeline = simplepbr.init()


        self.disableMouse()
        #self.pipeline = simplepbr.init()
        #self.render.setShaderAuto()
        #self.oobe()

        GlobalInstance.GameObject['base'] = self

        # Load files
        self.map = self.loader.loadModel("assets/models/map.bam")
        self.map.reparentTo(self.render)
        self.showMesh(self.map)
        #print(self.map.ls())

        for model in self.map.findAllMatches("**/HidingPlace*"):
            #model.node().setIntoCollideMask(CollideMask.bit(0))
            model.node().setIntoCollideMask(CollideMask.bit(1))

        #self.render_pipeline.prepare_scene(self.map)
        lightPos = self.map.find("**/LightPos*").getPos()

        #self.plane = self.loader.loadModel("assets/mesh.egg")
        #self.plane.reparentTo(self.render)
        self.navigationMesh = self.map.find("**/NavigationMesh")
        self.navigationMesh.hide()
        self.navigationMesh.detachNode()
        self.navigationGraph = NavGraph(self.navigationMesh)

        if USE_RP:
            slight = SpotLight()
            slight.pos = lightPos
            slight.fov = 60
            slight.energy = 1000
            slight.casts_shadows = True
            slight.shadow_map_resolution = 512
            slight.near_plane = 0.2
            slight.set_color_from_temperature(4000)
            #slight.look_at(0, 0, 0)
            self.render_pipeline.add_light(slight)

            self.flashlight = SpotLight()
            #self.flashlight.pos = self.camera.getPos()
            self.flashlight.fov = 50
            self.flashlight.radius = 25
            self.flashlight.energy = 50
            self.flashlight.casts_shadows = True
            self.flashlight.shadow_map_resolution = 512
            self.flashlight.near_plane = 0.2
            #self.flashlight.look_at(self.camera.getQuat().getForward())

            self.nearLight = PointLight()
            self.nearLight.energy = 0.1
            self.render_pipeline.add_light(self.nearLight)

            # this is for the bug where remove_light removes the passed light and the last light that was instantiated
            _plight = PointLight()
            _plight.energy = 0.1
            self.render_pipeline.add_light(_plight)
        else:
            slight = Spotlight("slight")
            slight.setColor((1.0, 0.82, 0.64, 1))
            #slight.attenuation = (1, 0, 1)
            lens = PerspectiveLens()
            lens.setFov(60)
            slight.setLens(lens)
            slnp = self.render.attachNewNode(slight)
            slnp.setPos(lightPos)
            slnp.lookAt(self.camera)
            self.render.setLight(slnp)

            slight = Spotlight("flashlight")
            slight.attenuation = (1, 0, 0.05)
            lens = PerspectiveLens()
            lens.setFov(50)
            slight.setLens(lens)
            self.flashlight = self.camera.attachNewNode(slight)

            plight = PointLight("plight")
            plight.setColor((1, 1, 1, 0.1))
            plight.attenuation = (1, 0, 1)
            self.nearLight = self.camera.attachNewNode(plight)
            self.render.setLight(self.nearLight)

        self.flashlightFloater = NodePath("flashlightFloater")
        self.flashlightFloater.setPos(0, 5, 0)
        self.flashlightFloater.reparentTo(self.camera)
        

        self.playerStartPos = self.map.find("**/StartPos").getPos()

        # camModel is only used for camera animation. Use self.camera for camera manipulation
        #self.camAnim = Actor("assets/models/camera.glb")
        self.camAnim = Actor("assets/models/camera.bam")
        self.camAnim.reparentTo(self.render)
        joint = self.camAnim.exposeJoint(None, "modelRoot", "CameraBone")
        self.camera.reparentTo(joint)

        self.camModel = NodePath("floater")
        self.camModel.reparentTo(joint)
        self.camera.reparentTo(self.camModel)
        #self.camera.setP(-45)

        self.enemy = Actor("assets/models/enemy.bam")
        self.enemy.reparentTo(self.render)
        self.enemyWalkAnim = self.enemy.getAnimControl("walk")
        self.enemyRunAnim = self.enemy.getAnimControl("run")
        self.showMesh(self.enemy)
        self.enemyColNp = self.enemy.find("**/+CollisionNode")

        self.enemy.node().setIntoCollideMask(CollideMask.bit(1))

        self.enemyStartPos = [model.getPos() for model in self.map.findAllMatches("**/EnemyPos*")]
        self.enemy.setPos(choice(self.enemyStartPos))

        self.pathfinder = PathFollower(self.enemy)

        self.enemyFloater = NodePath("enemyFloater")
        self.enemyFloater.setScale(0.2)
        self.enemyFloater.setPos(0, 1, 3)
        self.enemyFloater.reparentTo(self.enemy)


        self.backgroundMusic = self.loader.loadMusic("assets/sounds/Shattered_Mind.ogg")
        self.backgroundMusic.setVolume(0.01)
        self.backgroundMusic.setLoop(True)

        self.audio3d = Audio3DManager.Audio3DManager(self.sfxManagerList[0], self.camera)
        self.audio3d.setDropOffFactor(2)

        def add3DAudioToEnemy(filename):
            audio = self.audio3d.loadSfx(filename)
            audio.setLoop(True)
            self.audio3d.attachSoundToObject(audio, self.enemy)
            return audio

        self.chasingNoise = add3DAudioToEnemy("assets/sounds/enemy_chase.ogg")
        self.enemyStompingNoise = add3DAudioToEnemy("assets/sounds/enemy_stomping.ogg")
        self.enemyFastStompingNoise = add3DAudioToEnemy("assets/sounds/enemy_fast_stomping.ogg")

        self.enemyScream = self.loader.loadSfx("assets/sounds/enemy_scream.ogg")

        self.tiredNoise = self.loader.loadSfx("assets/sounds/tired.ogg")
        self.stompingNoise = self.loader.loadSfx("assets/sounds/stomping.ogg")
        self.stompingNoise.setLoop(True)
        self.fastStompingNoise = self.loader.loadSfx("assets/sounds/fast_stomping.ogg")
        self.fastStompingNoise.setLoop(True)


        '''plight = PointLight("plight")
        plight.setShadowCaster(True, 512, 512)
        plnp = self.render.attachNewNode(plight)
        plnp.setPos(5, -5, 8)
        self.render.setLight(plnp)'''
        '''alight = AmbientLight("alight")
        alight.setColor((.1, .1, .1, 1))
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)'''
        '''# render pipeline light
        my_light = PointLight()
        my_light.pos = (5, -5, 5)
        #my_light.radius = 1
        #my_light.inner_radius = 2
        my_light.color = (0.2, 0.6, 1.0)
        my_light.energy = 1000.0
        my_light.casts_shadows = True
        my_light.shadow_map_resolution = 512
        my_light.near_plane = 0.2
        self.render_pipeline.add_light(my_light)'''

        '''# panda3d AI
        self.AIworld = AIWorld(self.render)

        #self.AIchar = AICharacter("seeker", self.enemy, 100, 0.05, 5)
        self.AIchar = AICharacter("pursuer", self.enemy, 100, 0.05, 5)
        self.AIworld.addAiChar(self.AIchar)
        self.AIbehaviors = self.AIchar.getAiBehaviors()
        #self.AIbehaviors.obstacleAvoidance(0.02)
        #self.AIworld.addObstacle(self.map)
        self.AIbehaviors.initPathFind("assets/navmesh.csv")
        self.AIbehaviors.pathFindTo(self.camModel, 'addPath')

        #self.AIbehaviors.pursue(self.camModel)

        # panda3d AI'''


        ballPos = [axis.getPos() for axis in self.map.findAllMatches("**/BallPos*")]
        self.MAX_ITEMS = len(ballPos)
        #print(ballPos, len(ballPos))
        ballModel = self.map.find("**/ItemBall")
        self.items = []
        for pos in ballPos:
            _ball = ballModel.copyTo(self.map)
            _name = f"{_ball.getName()}_{pos}"
            _ball.setName(_name)
            _ball.setPos(pos)
            self.items.append(_name)
        ballModel.removeNode()

        drawer = self.map.find("**/ItemDrawer")
        drawer.hide()
        self.drawer = Actor("assets/models/drawer.glb")
        self.drawer.setHpr(drawer.getHpr(self.render))
        self.drawer.setPos(drawer.getPos(self.render))
        self.drawer.reparentTo(self.render)
        self.drawer = Drawer(self.drawer, "Key 1")

        #self.items = [np.getName() for np in self.map.findAllMatches("**/ItemBall*")]
        #self.items = [1, 2, 3, 4, 5]
        #print(self.items)


        self.mouseWatcherNode.set_modifier_buttons(ModifierButtons())
        self.buttonThrowers[0].node().set_modifier_buttons(ModifierButtons())

        self.accept('a', self.setKey, ['a', True])
        self.accept('d', self.setKey, ['d', True])
        self.accept('w', self.setKey, ['w', True])
        self.accept('s', self.setKey, ['s', True])
        self.accept('lshift', self.setKey, ['shift', True])
        self.accept('a-up', self.setKey, ['a', False])
        self.accept('d-up', self.setKey, ['d', False])
        self.accept('w-up', self.setKey, ['w', False])
        self.accept('s-up', self.setKey, ['s', False])
        self.accept('lshift-up', self.setKey, ['shift', False])

        self.accept("f11", self.toggleFullscreen)
        self.accept("mouse1", self.mouseClick)
        self.accept("mouse3", self.toggleFlashlight)
        self.accept("escape", sys.exit)
        self.accept("player-into-Enemy", self.playerIntoEnemy)
        # DEBUG
        def toggleEnemyChase():
            self.enemyChasing = not self.enemyChasing
        self.accept("q", toggleEnemyChase)
        self.accept("t", lambda: self.teleport(choice(self.enemyStartPos)+(0, 0, CAMERA_HEIGHT)))
        self.accept("e", self.pressE)
        def stashEnemy():
            self.enemyColNp.stash()
            print("enemyColNp stashed!")
        #self.accept("f", stashEnemy)
        #self.accept("g", self.gameOver)
        # DEBUG


        # set up collision detection ------------------------------
        self.cTrav = CollisionTraverser()
        #self.cTrav.showCollisions(self.render)
        ################################################################
        self.camLens.setNear(0.1)
        self.camLens.setFov(CAMERA_FOV)
        ################################################################

        self.camCol = CollisionNode('player')
        self.camCol.addSolid(CollisionSphere(center=(0, 0, -2), radius=0.5))
        self.camCol.addSolid(CollisionSphere(center=(0, -0.25, 0), radius=0.5))
        #self.camCol.setFromCollideMask(CollideMask.bit(0))
        #self.camCol.setIntoCollideMask(CollideMask.bit(0))
        self.camCol.setFromCollideMask(CollideMask.bit(1))
        self.camCol.setIntoCollideMask(CollideMask.bit(1))
        self.camColNp = self.camModel.attachNewNode(self.camCol)
        #self.camColNp.show()
        '''self.playerEnemyHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.camColNp, self.playerEnemyHandler)
        self.cTrav.showCollisions(self.render)'''

        self.pickerNode = CollisionNode('picker')
        self.pickerNode.addSolid(CollisionSegment(0, 0, 0, 0, 2.5, 0))
        #self.pickerNode.addSolid(CollisionSegment(0, 0, 0, 0, 5, 0))
        #self.pickerNode.setFromCollideMask(CollideMask.bit(0))
        self.pickerNode.setFromCollideMask(CollideMask.bit(1))
        self.pickerNode.setIntoCollideMask(CollideMask.allOff())
        self.pickerNp = self.camera.attachNewNode(self.pickerNode)
        #self.pickerNp.show()
        self.pickerHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.pickerNp, self.pickerHandler)

        self.enemyRayNp = self.enemy.attachNewNode(CollisionNode('enemyRay'))
        self.enemyRayNp.node().addSolid(CollisionRay(0, 1, CAMERA_HEIGHT, 0, 1, 0))
        #self.enemyCol.setFromCollideMask(CollideMask.bit(0))
        self.enemyRayNp.node().setFromCollideMask(CollideMask.bit(1))
        self.enemyRayNp.node().setIntoCollideMask(CollideMask.allOff())
        #self.enemyColNp.show()
        self.enemyRayHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.enemyRayNp, self.enemyRayHandler)

        '''self.enemyCol = CollisionNode('enemy')
        self.enemyCol.addSolid(CollisionSphere(center=(0, 0, 0), radius=1))
        self.enemyCol.setFromCollideMask(CollideMask.allOff())
        self.enemyCol.setIntoCollideMask(CollideMask.bit(1))
        #self.enemyColNp = self.enemy.attachNewNode(self.enemyCol)'''
        
        self.pusher = CollisionHandlerPusher()
        self.pusher.horizontal = True
        self.pusher.addInPattern("player-into-Enemy")

        self.pusher.addCollider(self.camColNp, self.camModel)
        #self.pusher.addCollider(self.enemyColNp, self.enemy)
        self.cTrav.addCollider(self.camColNp, self.pusher)
        #self.cTrav.addCollider(self.enemyColNp, self.pusher)
        '''self.enemyCol = CollisionNode('enemy')
        self.enemyColNp = self.enemy.attachNewNode(self.enemyCol)
        self.enemyColHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.enemyColNp, self.enemyColHandler)'''

        self.groundRay = CollisionRay()
        self.groundRay.setOrigin(0, 0, 9)
        self.groundRay.setDirection(0, 0, -1)
        self.groundCol = CollisionNode('groundRay')
        self.groundCol.addSolid(self.groundRay)
        #self.groundCol.setFromCollideMask(CollideMask.bit(0))
        self.groundCol.setFromCollideMask(CollideMask.bit(1))
        self.groundCol.setIntoCollideMask(CollideMask.allOff())
        self.groundColNp = self.camModel.attachNewNode(self.groundCol)
        self.groundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.groundColNp, self.groundHandler)

        self.cTrav.setRespectPrevTransform(True)


        # ---------- Puts the cursor image onscreen ----------
        self.cursorOnImage = OnscreenImage("assets/gui/cursor_on.png", scale=0.01)
        self.cursorOnImage.setTransparency(TransparencyAttrib.MAlpha)
        self.cursorOnImage.hide()

        self.cursorOffImage = OnscreenImage("assets/gui/cursor_off.png", scale=0.01)
        self.cursorOffImage.setTransparency(TransparencyAttrib.MAlpha)
        self.cursorOffImage.hide()
        
        self.pressEText = OnscreenText(text="", pos=(0, -0.1, 0), fg=(1, 1, 1, 1), parent=self.aspect2d)
        self.pressEText.hide()
        
        # ---------- Item Count ----------
        self.itemCountText = OnscreenText(text=f"0/{self.MAX_ITEMS} Items", scale=0.1, pos=(1.5, 0.9, 0), fg=(1, 1, 1, 1), parent=self.aspect2d)

        #self.camColNp.show()
        #self.groundColNp.show()
        #self.cTrav.showCollisions(self.render)
        # end collision detection

        # ---------- variables ----------
        self.fullscreen = False
        self.flashOn = False
        self.pitchMax, self.pitchMin = 40, -90

        self.taskMgr.add(self.update, "update")

        self.start()
    
    def start(self):
        # ---------- variables ----------
        self.inGame = False
        self.isGameOver = False
        if self.flashOn:
            self.toggleFlashlight()

        self.lastMouseX, self.lastMouseY = 0, 0
        self.rotateH, self.rotateP = 0, 0

        self.speed = PLAYER_SPEED
        self.isMoving = False
        self.isRunning = False
        self.isHiding = False
        self.hidePosInterval = None
        self.pickingOn = None
        self.beforeHidePos = (0, 0, 0)
        self.tired = False
        self.runTimer = Timer(5)
        self.runTimer.pause()
        self.tiredTimer = Timer(5)
        self.tiredTimer.pause()

        self._enemyChasing = False
        self.enemyChasing = False
        self.enemySeesPlayer = False
        self.enemySearching = False

        self.pathfinder.move_speed = ENEMY_SPEED

        self.keyMap = {
            'a': False, 'd': False,
            'w': False, 's': False,
            'shift': False,
        }

        self.enemyWalkAnim.loop("walk")

        self.backgroundMusic.play()

        self.cursorOffImage.show()
        self.cursorOnImage.hide()
        self.pressEText.setText("Press 'E' to hide")
        self.pressEText.hide()

        if USE_RP:
            self.nearLight.energy = 0.1
        else:
            self.nearLight.node().setColor((1, 1, 1, 0.1))

        self.camera.setHpr(0, -45, 0)
        self.camModel.setPos(self.playerStartPos + (0, 0, CAMERA_HEIGHT))
        self.camAnim.setPos(self.playerStartPos)
        self.camAnim.pose("shake", 0)

        self.enemy.setPos(choice(self.enemyStartPos))
        #self.taskMgr.doMethodLater(5, self.pathfinderUpdate, "pathfinderUpdate")
    
    # DEBUG
    def teleport(self, pos):
        posInterval = LerpPosInterval(
            nodePath=self.camModel,
            duration=1,
            pos=pos,
            blendType='easeInOut'
        )

        posInterval.start()
        return posInterval
    
    def goto(self, pos):
        self.pathfinder.follow_path(
            self.navigationGraph.find_path(self.enemy.getPos(), pos)
        )

    def update(self, task):
        if self.isGameOver:
            return task.cont
        
        self.playerMovement()
        self.enemyMovement()

        self.itemCountText.text = f"{self.MAX_ITEMS-len(self.items)}/{self.MAX_ITEMS} Items"

        '''if random() < 0.00_001: # 0.001% chance of playing every frame
            if self.backgroundMusic.status() != self.backgroundMusic.PLAYING:
                self.backgroundMusic.play()'''
        
        return task.cont
    
    def playerIntoEnemy(self, entry):
        if entry.getIntoNode().name != "Enemy" or self.isGameOver:
            return

        if self.enemyChasing and not self.enemySearching:
            self.gameOver()
    
    def gameOver(self):
        self.isGameOver = True
        
        self.pathfinder.stop()

        self.cursorOffImage.hide()
        self.cursorOnImage.hide()
        self.pressEText.hide()

        self.chasingNoise.stop()
        self.enemyStompingNoise.stop()
        self.enemyFastStompingNoise.stop()
        self.tiredNoise.stop()
        self.stompingNoise.stop()
        self.fastStompingNoise.stop()
        self.backgroundMusic.stop()

        #self.camModel.setPos(self.enemyFloater, 0, 1, 0)
        #self.camera.setH(-self.enemyFloater.getH(self.render))
        #self.camera.setP(-45)
        #self.enemy.setPos(self.camera, (0, 2, -CAMERA_HEIGHT))
        #self.enemy.setH(-self.camera.getH())
        #self.camAnim.setPos(self.camera.getPos(self.render))
        self.camAnim.setPos(self.enemyFloater, 0, 1, 0)
        self.camModel.setPos(self.camAnim, 0, 0, 0)
        self.camera.lookAt(self.enemyFloater)

        if USE_RP:
            self.nearLight.energy = 2
            self.nearLight.setPos(self.camera.getPos(self.render))
        else:
            self.nearLight.node().setColor((1, 1, 1, 0.5))

        self.camAnim.play("shake")
        self.enemyScream.play()

        self.taskMgr.doMethodLater(5, self.start, "startGame", extraArgs=[])
    
    def cameraMovement(self, dt):
        if USE_RP:
            self.flashlight.setPos(self.camera.getPos(self.render)+(0, 0.5, 0))
            self.flashlight.look_at(self.flashlightFloater.getPos(self.render))
            self.nearLight.setPos(self.camera.getPos(self.render))

        if self.inGame:
            mw = self.mouseWatcherNode
            if mw.hasMouse():
                x, y = mw.getMouseX(), mw.getMouseY()
                if self.lastMouseX is not None:
                    dx, dy = x, y
                else:
                    dx, dy = 0, 0
                self.lastMouseX, self.lastMouseY = x, y
            else:
                self.toggleIngame()
                x, y, dx, dy = 0, 0, 0, 0
            self.recenterCursor()
            self.lastMouseX, self.lastMouseY = 0, 0
            
            self.rotateH -= dx * dt * 1500
            self.rotateP += dy * dt * 1000

            if self.rotateP > self.pitchMax:
                self.rotateP -= self.rotateP - self.pitchMax
            elif self.rotateP < self.pitchMin:
                self.rotateP -= self.rotateP - self.pitchMin

            self.camera.setH(self.rotateH)
            self.camera.setP(self.rotateP)
    
    def enemyMovement(self):
        if self.enemyChasing:
            if self.chasingNoise.status() != self.chasingNoise.PLAYING:
                self.chasingNoise.play()
            if self.enemyFastStompingNoise.status() != self.enemyFastStompingNoise.PLAYING:
                self.enemyFastStompingNoise.play()
            if self.enemyStompingNoise.status() == self.enemyStompingNoise.PLAYING:
                self.enemyStompingNoise.stop()

            if self.enemyWalkAnim.isPlaying():
                self.enemyRunAnim.loop("run")

            self.pathfinder.move_speed = ENEMY_SPEED * 2
            try:
                if self._enemyChasing != self.enemyChasing:
                    if not self.pathfinder.seq.isPlaying():
                        self.goto(self.camera.getPos(self.render))
                    else:
                        self.pathfinder.stop()
                    self._enemyChasing = self.enemyChasing
                else:
                    if not self.pathfinder.seq.isPlaying():
                        self.goto(self.camera.getPos(self.render))
            except:
                pass
        elif self.enemySearching:
            if self.isHiding:
                if not self.pathfinder.seq.isPlaying():
                    self.enemySearching = False
            else:
                self.enemySearching = False
                self.enemyChasing = True
        else:
            if self.chasingNoise.status() == self.chasingNoise.PLAYING:
                self.chasingNoise.stop()
            if self.enemyFastStompingNoise.status() == self.enemyFastStompingNoise.PLAYING:
                self.enemyFastStompingNoise.stop()
            if self.enemyStompingNoise.status() != self.enemyStompingNoise.PLAYING:
                self.enemyStompingNoise.play()

            if self.enemyRunAnim.isPlaying():
                self.enemyWalkAnim.loop("walk")
            
            self.pathfinder.move_speed = ENEMY_SPEED
            try:
                if self._enemyChasing != self.enemyChasing:
                    if not self.pathfinder.seq.isPlaying():
                        self.goto(choice(self.enemyStartPos))
                    else:
                        self.pathfinder.stop()
                    self._enemyChasing = self.enemyChasing
                else:
                    if not self.pathfinder.seq.isPlaying():
                        self.goto(choice(self.enemyStartPos))
            except:
                pass
        
        self.pathfinder._update()
        #self.enemy.setH(180)
        self.enemy.setZ(0)
        self.enemy.setP(0)

        #print("enemySeesPlayer:", self.enemySeesPlayer)
        #print("enemySearching:", self.enemySearching)
        #print("enemyChasing:", self.enemyChasing)
        
        self.enemyRayNp.lookAt(self.camModel.getPos(self.enemy) - (0, 0, 3))
        if self.enemyRayHandler.getNumEntries(): # if there are any entries
            self.enemyRayHandler.sortEntries()
            firstEntry = list(self.enemyRayHandler.entries)[0]

            if firstEntry.getIntoNode().name == 'player':
                self.enemySeesPlayer = True
                hpr = self.enemyRayNp.getHpr()
                if hpr < ENEMY_FOV and hpr > -ENEMY_FOV:
                    if not self.isHiding:
                        self.enemyChasing = True
                        self.enemyColNp.unstash()
            else:
                self.enemySeesPlayer = False
    
    # player movement
    def playerMovement(self):
        dt = self.taskMgr.globalClock.getDt()

        self.cameraMovement(dt)


        if not self.isHiding and (self.keyMap['a'] or self.keyMap['d'] or self.keyMap['w'] or self.keyMap['s']):
            self.isMoving = True
            if self.stompingNoise.status() != self.stompingNoise.PLAYING and not self.isRunning:
                self.stompingNoise.play()
            self.camAnim.setPlayRate(1.0, 'bob')
            self.camAnim.loop('bob', restart=0)
        else:
            self.isMoving = False
            self.stompingNoise.stop()
            self.camAnim.stop()
        
        if not self.isHiding and (self.keyMap['shift'] and self.isMoving and not self.tired):
            self.isRunning = True
            self.speed = PLAYER_SPEED * 2
        else:
            self.isRunning = False
            self.speed = PLAYER_SPEED
        
        if self.isRunning:
            self.runTimer.resume()
            if self.fastStompingNoise.status() != self.fastStompingNoise.PLAYING:
                self.stompingNoise.stop()
                self.fastStompingNoise.play()
            self.camAnim.setPlayRate(1.5, 'bob')
        else:
            self.fastStompingNoise.stop()
            self.runTimer.pause()
        
        if self.runTimer.timeIsUp():
            self.tired = True
            self.tiredNoise.play()
            self.runTimer.reset()
            self.runTimer.pause()
            self.tiredTimer.reset()
        elif self.tiredTimer.timeIsUp():
            self.tired = False
            self.tiredTimer.reset()
            self.tiredTimer.pause()
            self.runTimer.reset()

        if self.isHiding:
            return
        
        if self.keyMap['a']:
            self.camModel.setFluidX(self.camera, -self.speed * dt)
        if self.keyMap['d']:
            self.camModel.setFluidX(self.camera, +self.speed * dt)
        if self.keyMap['w']:
            self.camModel.setFluidY(self.camera, +self.speed * dt)
        if self.keyMap['s']:
            self.camModel.setFluidY(self.camera, -self.speed * dt)
        #self.camera.setZ(3)

        
        groundEntries = list(self.groundHandler.entries)
        groundEntries.sort(key=lambda x: x.getSurfacePoint(self.render).getZ())
        
        for entry in groundEntries:
            if entry.getIntoNode().name == 'Ground':
                self.camModel.setFluidZ(entry.getSurfacePoint(self.render).getZ()+CAMERA_HEIGHT)


        # ---------- picker event ----------
        if self.pickerHandler.getNumEntries() > 1: # if there are any entries
            self.pickerHandler.sortEntries()
            entry = self.pickerHandler.entries[1].getIntoNodePath()
            entryName = entry.getName()

            if entryName.startswith("HidingPlace") or entryName.startswith("Item"):
                self.cursorOffImage.hide()
                self.cursorOnImage.show()
                if entryName.startswith("HidingPlace"):
                    if self.isHiding:
                        self.pressEText.setText("Press 'E' to leave")
                    else:
                        self.pressEText.setText("Press 'E' to hide")
                # EASTER EGG
                elif entryName.startswith("ItemDrawer"):
                    self.pressEText.setText("Press 'E' to open")
                else: # if entryName.startswith("Item"):
                    self.pressEText.setText("Press 'E' to collect item")
                self.pressEText.show()
                self.pickingOn = entry
            else:
                self.pressEText.hide()
                self.cursorOnImage.hide()
                self.cursorOffImage.show()
                self.pickingOn = None
        else:
            self.pressEText.hide()
            self.cursorOnImage.hide()
            self.cursorOffImage.show()
            self.pickingOn = None
        
        '''# ---------- player and enemy event ----------
        if self.playerEnemyHandler.getNumEntries():
            print("playerEnemyHandler!")
            for entry in self.playerEnemyHandler.entries:
                print(entry.getIntoNode().name)
                if entry.getIntoNode().name == "Enemy":
                    self.gameOver()'''
    
    # Records the state of the wasd and shift keys
    def setKey(self, key, value):
        self.keyMap[key] = value
    
    def toggleFlashlight(self):
        self.flashOn = not self.flashOn

        if self.flashOn:
            if USE_RP:
                self.render_pipeline.add_light(self.flashlight)
            else:
                self.render.setLight(self.flashlight)
        else:
            if USE_RP:
                self.render_pipeline.remove_light(self.flashlight)
            else:
                self.render.clearLight(self.flashlight)
    
    # Toggles fullscreen
    def toggleFullscreen(self):
        self.fullscreen = not self.fullscreen

        wp = WindowProperties()
        wp.fullscreen = self.fullscreen
        if self.fullscreen:
            wp.size = (1920, 1080)
        else:
            wp.size = (1280, 720)
            wp.origin = (-2, -2)
            wp.fixed_size = True
        self.win.requestProperties(wp)


    # Toggles if player is in game
    def toggleIngame(self):
        if self.isGameOver:
            return
        self.inGame = not self.inGame

        wp = WindowProperties()
        wp.setCursorHidden(self.inGame)
        if self.inGame:
            wp.setMouseMode(WindowProperties.M_confined)
        else:
            wp.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(wp)
    

    # Recenters the cursor position
    def recenterCursor(self):
        self.win.movePointer(
            0,
            int(self.win.getProperties().getXSize() / 2),
            int(self.win.getProperties().getYSize() / 2)
        )
    
    # Method that gets called every time left mouse button is clicked
    def mouseClick(self):
        if self.inGame:
            pass
        else:
            self.toggleIngame()
    
    # Method that gets called every time 'E' button is pressed
    def pressE(self):
        if not self.inGame or not self.pickingOn:
            return
        if self.hidePosInterval and self.hidePosInterval.isPlaying():
            return

        if self.pickingOn:
            colName = self.pickingOn.getName()
            if colName.startswith("HidingPlace"):
                if self.isHiding:
                    pos = self.beforeHidePos
                    self.enemyColNp.unstash()
                else:
                    self.beforeHidePos = self.camModel.getPos()
                    pos = self.pickingOn.getPos(self.render)

                    if self.enemyChasing:
                        if not self.enemySeesPlayer:
                            self.goto(self.beforeHidePos)
                            self.enemySearching = True
                            self.enemyChasing = False
                            self.enemyColNp.stash()
                    
                self.hidePosInterval = self.teleport(pos)
                self.isHiding = not self.isHiding
                if self.isHiding:
                    self.pressEText.setText("Press 'E' to leave")
                else:
                    self.pressEText.setText("Press 'E' to hide")

            elif colName.startswith("Item"):
                if colName == "ItemDrawer":
                    self.drawer.toggle()
                elif colName.startswith("ItemBall"):
                    ball = self.map.find("**/"+colName+"_"+str(self.pickingOn.getPos(self.render)))
                    self.items.remove(ball.getName())
                    ball.removeNode()
    
    def showMesh(self, model):
        for node in model.findAllMatches("**/+CollisionNode"):
            parent = node.getParent()
            for geomNode in parent.findAllMatches('**/+GeomNode'):
                #print(geomNode)
                geomNode.reparentTo(parent)
    
    def createCollisionMesh(self, modelRoot):
        # create a temporary copy to generate the collision meshes from
        modelCopy = modelRoot.copyTo(self.render)
        modelCopy.detachNode()
        # "bake" the transformations into the vertices
        modelCopy.flattenLight()

        # create root node to attach collision nodes to
        collisionRoot = NodePath("collisionRoot")
        collisionRoot.reparentTo(modelRoot)
        # offset the collision meshes from the model so they're easier to see
        #collisionRoot.setX(1.)

        # create a collision mesh for each of the loaded models
        for model in modelCopy.findAllMatches("**/+GeomNode"):
            modelNode = model.node()
            collisionNode = CollisionNode(modelNode.name)
            collisionMesh = collisionRoot.attachNewNode(collisionNode)
            collisionMesh.show()

            for geom in modelNode.modifyGeoms():
                geom.decomposeInPlace()
                vertexData = geom.modifyVertexData()
                vertexData.format = GeomVertexFormat.getV3()
                view = memoryview(vertexData.arrays[0]).cast("B").cast("f")
                indexList = geom.primitives[0].getVertexList()
                indexCount = len(indexList)

                for indices in (indexList[i:i+3] for i in range(0, indexCount, 3)):
                    points = [Point3(*view[index*3:index*3+3]) for index in indices]
                    collPoly = CollisionPolygon(*points)
                    collisionNode.addSolid(collPoly)

game = Game()
game.run()