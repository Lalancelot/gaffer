##########################################################################
#
#  Copyright (c) 2011-2012, John Haddon. All rights reserved.
#  Copyright (c) 2011-2013, Image Engine Design Inc. All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#      * Redistributions of source code must retain the above
#        copyright notice, this list of conditions and the following
#        disclaimer.
#
#      * Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided with
#        the distribution.
#
#      * Neither the name of John Haddon nor the names of
#        any other contributors to this software may be used to endorse or
#        promote products derived from this software without specific prior
#        written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
#  IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#  THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#  PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
#  CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#  EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
#  PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
#  LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#  NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
##########################################################################

import unittest
import threading
import time

import IECore

import Gaffer
import GafferTest

class ComputeNodeTest( GafferTest.TestCase ) :

	def testOperation( self ) :

		n1 = GafferTest.AddNode()
		n1["sum"].getValue()

		dirtiedPlugs = GafferTest.CapturingSlot( n1.plugDirtiedSignal() )
		setPlugs = GafferTest.CapturingSlot( n1.plugSetSignal() )

		n1["op1"].setValue( 2 )
		self.assertEqual( len( setPlugs ), 1 )
		self.assertEqual( len( dirtiedPlugs ), 2 )
		self.assertEqual( setPlugs[0][0].fullName(), "AddNode.op1" )
		self.assertEqual( dirtiedPlugs[0][0].fullName(), "AddNode.op1" )
		self.assertEqual( dirtiedPlugs[1][0].fullName(), "AddNode.sum" )

		n1["op2"].setValue( 3 )
		self.assertEqual( len( setPlugs ), 2 )
		self.assertEqual( setPlugs[1][0].fullName(), "AddNode.op2" )

		del dirtiedPlugs[:]
		del setPlugs[:]

		# plug set or dirty signals are not emitted during computation
		self.assertEqual( n1.getChild("sum").getValue(), 5 )
		self.assertEqual( len( setPlugs ), 0 )
		self.assertEqual( len( dirtiedPlugs ), 0 )

		# connect another add node onto the output of this one

		n2 = GafferTest.AddNode( "Add2" )

		dirtiedPlugs2 = GafferTest.CapturingSlot( n2.plugDirtiedSignal() )
		setPlugs2 = GafferTest.CapturingSlot( n2.plugSetSignal() )

		n2["op1"].setInput( n1["sum"] )
		# connecting a plug doesn't set the value of the input plug
		# immediately - the value is transferred only upon request.
		self.assertEqual( len( setPlugs2 ), 0 )
		self.assertEqual( len( dirtiedPlugs2 ), 2 )
		self.assertEqual( dirtiedPlugs2[0][0].fullName(), "Add2.op1" )
		self.assertEqual( dirtiedPlugs2[1][0].fullName(), "Add2.sum" )

		del dirtiedPlugs2[:]
		del setPlugs2[:]

		self.assertEqual( n2["op1"].getValue(), 5 )
		self.assertEqual( n2["sum"].getValue(), 5 )

		# plug set or dirty signals are not emitted during computation
		self.assertEqual( len( setPlugs2 ), 0 )
		self.assertEqual( len( dirtiedPlugs2 ), 0 )

	def testDirtyOfInputsWithConnections( self ) :

		n1 = GafferTest.AddNode( "n1" )
		n2 = GafferTest.AddNode( "n2" )

		dirtied = GafferTest.CapturingSlot( n1.plugDirtiedSignal(), n2.plugDirtiedSignal() )

		n2["op1"].setInput( n1["sum"] )
		self.assertEqual( len( dirtied ), 2 )
		self.failUnless( dirtied[0][0].isSame( n2["op1"] ) )
		self.failUnless( dirtied[1][0].isSame( n2["sum"] ) )

		del dirtied[:]
		n1["op1"].setValue( 10 )
		self.assertEqual( len( dirtied ), 4 )
		self.failUnless( dirtied[0][0].isSame( n1["op1"] ) )
		self.failUnless( dirtied[1][0].isSame( n1["sum"] ) )
		self.failUnless( dirtied[2][0].isSame( n2["op1"] ) )
		self.failUnless( dirtied[3][0].isSame( n2["sum"] ) )

		self.assertEqual( n2.getChild( "sum" ).getValue(), 10 )

	def testDirtyPlugComputesSameValueAsBefore( self ) :

		n1 = GafferTest.AddNode( "N1" )
		n2 = GafferTest.AddNode( "N2" )

		n2.getChild( "op1" ).setInput( n1.getChild( "sum" ) )

		n1.getChild( "op1" ).setValue( 1 )
		n1.getChild( "op2" ).setValue( -1 )

		self.assertEqual( n2.getChild( "sum" ).getValue(), 0 )

	def testOutputsDirtyForNewNodes( self ) :

		n = GafferTest.AddNode()
		n["op1"].setValue( 1 )
		n["op2"].setValue( 2 )

		self.assertEqual( n["sum"].getValue(), 3 )

	def testComputeInContext( self ) :

		n = GafferTest.FrameNode()
		self.assertEqual( n["output"].getValue(), 1 )

		c = Gaffer.Context()
		c.setFrame( 10 )

		with c :
			self.assertEqual( n["output"].getValue(), 10 )

	def testComputeInThreads( self ) :

		n = GafferTest.FrameNode()

		def f( frame ) :

			c = Gaffer.Context()
			c.setFrame( frame )

			with c :
				time.sleep( 0.01 )
				self.assertEqual( n["output"].getValue(), frame )

		threads = []
		for i in range( 0, 1000 ) :

			t = threading.Thread( target = f, args = ( i, ) )
			t.start()
			threads.append( t )

		for t in threads :
			t.join()

	def testDirtyNotPropagatedDuringCompute( self ) :

		n1 = GafferTest.AddNode( "n1" )
		n2 = GafferTest.AddNode( "n2" )

		n1["op1"].setValue( 2 )
		n1["op2"].setValue( 3 )
		n2["op1"].setInput( n1["sum"] )

		dirtyCapturer = GafferTest.CapturingSlot( n2.plugDirtiedSignal() )

		self.assertEqual( n2["sum"].getValue(), 5 )

		self.assertEqual( len( dirtyCapturer ), 0 )

	def testWrongPlugSet( self ) :

		n = GafferTest.BadNode()
		self.assertRaises( RuntimeError, n["out1"].getValue )

	def testPlugNotSet( self ) :

		n = GafferTest.BadNode()
		self.assertRaises( RuntimeError, n["out3"].getValue )

	def testHash( self ) :

		n = GafferTest.MultiplyNode()
		self.assertHashesValid( n )

	def testHashForPythonDerivedClasses( self ) :

		n = GafferTest.AddNode()
		self.assertHashesValid( n )

	def testDisableCaching( self ) :

		n = GafferTest.CachingTestNode()

		n["in"].setValue( "d" )

		v1 = n["out"].getValue( _copy=False )
		v2 = n["out"].getValue( _copy=False )

		self.assertEqual( v1, v2 )
		self.assertEqual( v1, IECore.StringData( "d" ) )

		# the objects should be one and the same, as the second computation
		# should have shortcut and returned a cached result.
		self.failUnless( v1.isSame( v2 ) )

		n["out"].setFlags( Gaffer.Plug.Flags.Cacheable, False )
		v3 = n["out"].getValue( _copy=False )

		self.assertEqual( v3, IECore.StringData( "d" ) )
		self.assertEqual( v3, v1 )

		# we disabled caching, so the two values should
		# be distinct objects, even though they are equal.
		self.failIf( v3.isSame( v1 ) )

	def testConnectedPlugsShareHashesAndCacheEntries( self ) :

		class Out( Gaffer.ComputeNode ) :

			def __init__( self, name="Out" ) :

				Gaffer.ComputeNode.__init__( self, name )

				self.addChild( Gaffer.ObjectPlug( "oOut", Gaffer.Plug.Direction.Out, IECore.NullObject() ) )
				self.addChild( Gaffer.FloatPlug( "fOut", Gaffer.Plug.Direction.Out ) )

			def affects( self, input ) :

				return []

			def hash( self, output, context, h ) :

				h.append( context.getFrame() )

			def compute( self, plug, context ) :

				if plug.getName() == "oOut" :
					plug.setValue( IECore.IntData( int( context.getFrame() ) ) )
				else :
					plug.setValue( context.getFrame() )

		IECore.registerRunTimeTyped( Out )

		class In( Gaffer.ComputeNode ) :

			def __init__( self, name="In" ) :

				Gaffer.ComputeNode.__init__( self, name )

				self.addChild( Gaffer.ObjectPlug( "oIn", Gaffer.Plug.Direction.In, IECore.NullObject() ) )
				self.addChild( Gaffer.IntPlug( "iIn", Gaffer.Plug.Direction.In ) )

		IECore.registerRunTimeTyped( In )

		nOut = Out()
		nIn = In()

		nIn["oIn"].setInput( nOut["oOut"] )
		nIn["iIn"].setInput( nOut["fOut"] )

		for i in range( 0, 1000 ) :

			c = Gaffer.Context()
			c.setFrame( i )
			with c :

				# because oIn and oOut are connected, they should
				# have the same hash and share the exact same value.

				self.assertEqual( nIn["oIn"].getValue(), IECore.IntData( i ) )
				self.assertEqual( nOut["oOut"].getValue(), IECore.IntData( i ) )

				self.assertEqual( nIn["oIn"].hash(), nOut["oOut"].hash() )
				self.failUnless( nIn["oIn"].getValue( _copy=False ).isSame( nOut["oOut"].getValue( _copy=False ) ) )

				# even though iIn and fOut are connected, they should have
				# different hashes and different values, because type conversion
				# (float to int) is performed when connecting them.

				self.assertEqual( nIn["iIn"].getValue(), i )
				self.assertEqual( nOut["fOut"].getValue(), float( i ) )

				self.assertNotEqual( nIn["iIn"].hash(), nOut["fOut"].hash() )

	class PassThrough( Gaffer.ComputeNode ) :

		def __init__( self, name="PassThrough", inputs={}, dynamicPlugs=() ) :

			Gaffer.ComputeNode.__init__( self, name )

			self.addChild( Gaffer.ObjectPlug( "in", Gaffer.Plug.Direction.In, IECore.NullObject() ) )
			self.addChild( Gaffer.ObjectPlug( "out", Gaffer.Plug.Direction.Out, IECore.NullObject() ) )

		def affects( self, input ) :

			if input.isSame( self["in"] ) :
				return [ self["out"] ]

			return []

		def hash( self, output, context, h ) :

			assert( output.isSame( self["out"] ) )

			# by assigning directly to the hash rather than appending,
			# we signify that we'll pass through the value unchanged.
			h.copyFrom( self["in"].hash() )

		def compute( self, plug, context ) :

			assert( plug.isSame( self["out"] ) )

			plug.setValue( self["in"].getValue( _copy=False ), _copy=False )

	IECore.registerRunTimeTyped( PassThrough )

	def testPassThroughSharesHashes( self ) :

		n = self.PassThrough()
		n["in"].setValue( IECore.MeshPrimitive.createPlane( IECore.Box2f( IECore.V2f( -1 ), IECore.V2f( 1 ) ) ) )

		self.assertEqual( n["in"].hash(), n["out"].hash() )
		self.assertEqual( n["in"].getValue(), n["out"].getValue() )

	def testPassThroughSharesCacheEntries( self ) :

		n = self.PassThrough()
		n["in"].setValue( IECore.MeshPrimitive.createPlane( IECore.Box2f( IECore.V2f( -1 ), IECore.V2f( 1 ) ) ) )

		# this fails because TypedObjectPlug::setValue() currently does a copy. i think we can
		# optimise things by allowing a copy-free setValue() function for use during computations.
		self.failUnless( n["in"].getValue( _copy=False ).isSame( n["out"].getValue( _copy=False ) ) )

	def testInternalConnections( self ) :

		a = GafferTest.AddNode()
		a["op1"].setValue( 10 )

		n = Gaffer.Node()
		n["in"] = Gaffer.IntPlug()
		n["out"] = Gaffer.IntPlug( direction = Gaffer.Plug.Direction.Out )
		n["out"].setInput( n["in"] )

		n["in"].setInput( a["sum"] )

		self.assertEqual( n["out"].getValue(), a["sum"].getValue() )
		self.assertEqual( n["out"].hash(), a["sum"].hash() )

	def testErrorSignal( self ) :

		b = GafferTest.BadNode()
		a = GafferTest.AddNode()
		a["op1"].setInput( b["out3"] )

		cs = GafferTest.CapturingSlot( b.errorSignal() )

		self.assertRaises( RuntimeError, b["out1"].getValue )
		self.assertEqual( len( cs ), 1 )
		self.assertTrue( cs[0][0].isSame( b["out1"] ) )
		self.assertTrue( cs[0][1].isSame( b["out1"] ) )
		self.assertTrue( isinstance( cs[0][2], str ) )

		self.assertRaises( RuntimeError, a["sum"].getValue )
		self.assertEqual( len( cs ), 2 )
		self.assertTrue( cs[1][0].isSame( b["out3"] ) )
		self.assertTrue( cs[1][1].isSame( b["out3"] ) )
		self.assertTrue( isinstance( cs[1][2], str ) )

	def testErrorSignalledOnIntermediateNodes( self ) :

		nodes = [ GafferTest.BadNode() ]
		for i in range( 0, 10 ) :

			nodes.append( GafferTest.AddNode() )
			nodes[-1]["op1"].setInput(
				nodes[-2]["sum"] if i != 0 else nodes[-2]["out3"]
			)

		slots = [ GafferTest.CapturingSlot( n.errorSignal() ) for n in nodes ]

		self.assertRaises( RuntimeError, nodes[-1]["sum"].getValue )
		for i, slot in enumerate( slots ) :
			self.assertEqual( len( slot ), 1 )
			self.assertTrue( slot[0][0].isSame( nodes[i]["out3"] if i == 0 else nodes[i]["sum"] ) )
			self.assertTrue( slot[0][1].isSame( nodes[0]["out3"] ) )

	def testErrorSignalledAtScopeTransitions( self ) :

		s = Gaffer.ScriptNode()
		s["b"] = Gaffer.Box()
		s["b"]["b"] = GafferTest.BadNode()
		s["b"]["a"] = GafferTest.AddNode()
		s["b"]["a"]["op1"].setInput( s["b"]["b"]["out3"] )

		css = GafferTest.CapturingSlot( s.errorSignal() )
		csb = GafferTest.CapturingSlot( s["b"].errorSignal() )
		csbb = GafferTest.CapturingSlot( s["b"]["b"].errorSignal() )

		p = s["b"].promotePlug( s["b"]["a"]["sum"], asUserPlug = False )

		self.assertRaises( RuntimeError, p.getValue )
		self.assertEqual( len( css ), 0 )
		self.assertEqual( len( csb ), 1 )
		self.assertTrue( csb[0][0].isSame( p ) )
		self.assertTrue( csb[0][1].isSame( s["b"]["b"]["out3"] ) )
		self.assertEqual( len( csbb ), 1 )
		self.assertTrue( csbb[0][0].isSame( s["b"]["b"]["out3"] ) )
		self.assertTrue( csbb[0][1].isSame( s["b"]["b"]["out3"] ) )

if __name__ == "__main__":
	unittest.main()
