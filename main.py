from panda3d.core import loadPrcFileData

conf = """
win-size 1280 720
win-fixed-size 1
window-title Ghost Runner
show-frame-rate-meter 1
textures-power-2 none
#fullscreen true
"""

loadPrcFileData("", conf)

from panda3d.core import WindowProperties, ModifierButtons, \
    PointLight, \
    CollisionTraverser, CollisionHandlerQueue, CollisionHandlerPusher, CollisionNode, CollisionPolygon, CollisionRay, CollisionSphere, CollideMask, \
    GeomVertexFormat, NodePath, Point3

from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from base_objects import *
import GlobalInstance
from random import choice
import sys

pipeline_path = "/home/joey/dev/panda_3d/RenderPipeline/"
sys.path.insert(0, pipeline_path)
#from rpcore import RenderPipeline, PointLight
import simplepbr

PLAYER_SPEED = 4
CAMERA_HEIGHT = 3

class Game(ShowBase):
    def __init__(self):
        super().__init__()
        '''# ----- Begin of render pipeline code -----
        self.render_pipeline = RenderPipeline()
        self.render_pipeline.create(self)

        self.render_pipeline.daytime_mgr.time = "7:40"
        # ----- End of render pipeline code -----'''
        
        self.disableMouse()
        self.pipeline = simplepbr.init()
        #self.oobe()

        GlobalInstance.GameObject['base'] = self

        # Load files
        self.map = self.loader.loadModel("assets/map.bam")
        self.map.reparentTo(self.render)
        self.showMesh(self.map)
        #self.render_pipeline.prepare_scene(self.map)

        startPos = self.map.find("**/StartPos").getPos()

        # camModel is only used for camera animation. Use self.camera for camera manipulation
        self.camAnim = Actor("assets/camera.glb")
        self.camAnim.reparentTo(self.render)
        joint = self.camAnim.exposeJoint(None, "modelRoot", "CameraBone")
        self.camera.reparentTo(joint)

        self.camModel = NodePath("floater")
        self.camModel.reparentTo(joint)
        self.camModel.setPos(startPos + (0, 0, CAMERA_HEIGHT))
        self.camera.reparentTo(self.camModel)
        #self.camera.setP(-45)

        self.enemy = Actor("assets/enemy.bam")
        self.enemy.reparentTo(self.render)
        self.showMesh(self.enemy)

        self.enemyStartPos = [model.getPos() for model in self.map.findAllMatches("**/EnemyPos*")]
        self.enemy.setPos(choice(self.enemyStartPos))

        self.tiredNoise = self.loader.loadSfx("assets/tired.ogg")
        self.stompingNoise = self.loader.loadSfx("assets/stomping.ogg")
        self.stompingNoise.setLoop(True)
        self.fastStompingNoise = self.loader.loadSfx("assets/fast_stomping.ogg")
        self.fastStompingNoise.setLoop(True)


        plight = PointLight("plight")
        plnp = self.render.attachNewNode(plight)
        plnp.setPos(5, -5, 18)
        self.render.setLight(plnp)
        '''# render pipeline light
        my_light = PointLight()
        my_light.pos = (5, -20, 15)
        my_light.radius = 1
        my_light.inner_radius = 2
        my_light.color = (0.2, 0.6, 1.0)
        my_light.energy = 1000.0
        my_light.casts_shadows = True
        my_light.shadow_map_resolution = 512
        my_light.near_plane = 0.2
        self.render_pipeline.add_light(my_light)'''


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
        self.accept("escape", sys.exit)


        # set up collision detection ------------------------------
        self.cTrav = CollisionTraverser()
        ################################################################
        self.camLens.setNear(0.1)
        self.camLens.setFov(90)
        ################################################################

        self.camCol = CollisionNode('camera')
        self.camCol.addSolid(CollisionSphere(center=(0, 0, -2), radius=0.5))
        self.camCol.addSolid(CollisionSphere(center=(0, -0.25, 0), radius=0.5))
        self.camCol.setFromCollideMask(CollideMask.bit(0))
        self.camCol.setIntoCollideMask(CollideMask.allOff())
        self.camColNp = self.camModel.attachNewNode(self.camCol)
        self.camPusher = CollisionHandlerPusher()
        self.camPusher.horizontal = True

        self.camPusher.addCollider(self.camColNp, self.camModel)
        self.cTrav.addCollider(self.camColNp, self.camPusher)

        self.groundRay = CollisionRay()
        self.groundRay.setOrigin(0, 0, 9)
        self.groundRay.setDirection(0, 0, -1)
        self.groundCol = CollisionNode('groundRay')
        self.groundCol.addSolid(self.groundRay)
        self.groundCol.setFromCollideMask(CollideMask.bit(0))
        self.groundCol.setIntoCollideMask(CollideMask.allOff())
        self.groundColNp = self.camModel.attachNewNode(self.groundCol)
        self.groundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.groundColNp, self.groundHandler)

        self.cTrav.setRespectPrevTransform(True)

        #self.camColNp.show()
        #self.groundColNp.show()
        #self.cTrav.showCollisions(self.render)
        # end collision detection


        self.start()
    
    def start(self):
        # variables
        self.inGame = False
        self.isGameOver = False
        self.fullscreen = False
        self.lastMouseX, self.lastMouseY = None, None
        self.rotateH, self.rotateP = 0, 0
        self.pitchMax, self.pitchMin = 40, -90
        self.speed = PLAYER_SPEED
        self.isMoving = False
        self.isRunning = False
        self.tired = False
        self.runTimer = Timer(5)
        self.runTimer.pause()
        self.tiredTimer = Timer(5)
        self.tiredTimer.pause()

        self.keyMap = {
            'a': False, 'd': False,
            'w': False, 's': False,
            'shift': False,
        }

        self.taskMgr.add(self.update, "update")

    def update(self, task):
        dt = self.taskMgr.globalClock.getDt()

        self.movement()
        
        return task.cont
    
    def movement(self):
        dt = self.taskMgr.globalClock.getDt()

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

        if self.keyMap['a'] or self.keyMap['d'] or self.keyMap['w'] or self.keyMap['s']:
            self.isMoving = True
            if self.stompingNoise.status() != self.stompingNoise.PLAYING and not self.isRunning:
                self.stompingNoise.play()
            self.camAnim.setPlayRate(1.0, 'bob')
            self.camAnim.loop('bob', restart=0)
        else:
            self.isMoving = False
            self.stompingNoise.stop()
            self.camAnim.stop()
        
        if self.keyMap['shift'] and self.isMoving and not self.tired:
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
        
        
        if self.keyMap['a']:
            self.camModel.setFluidX(self.camera, -self.speed * dt)
        if self.keyMap['d']:
            self.camModel.setFluidX(self.camera, +self.speed * dt)
        if self.keyMap['w']:
            self.camModel.setFluidY(self.camera, +self.speed * dt)
        if self.keyMap['s']:
            self.camModel.setFluidY(self.camera, -self.speed * dt)
        #self.camera.setZ(3)

        
        entries = list(self.groundHandler.entries)
        entries.sort(key=lambda x: x.getSurfacePoint(self.render).getZ())
        
        for entry in entries:
            if entry.getIntoNode().name == 'Terrain':
                self.camModel.setFluidZ(entry.getSurfacePoint(self.render).getZ()+CAMERA_HEIGHT)
    
    # Records the state of the wasd keys
    def setKey(self, key, value):
        self.keyMap[key] = value
    
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
    
    def showMesh(self, model):
        for node in model.findAllMatches("**/+CollisionNode"):
            parent = node.getParent()
            for geomNode in parent.findAllMatches('**/+GeomNode'):
                geomNode.reparent_to(parent)
    
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